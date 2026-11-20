"""Data coordinator for Fazilet Takvimi."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    BASE_URL,
    CONF_PATH,
    CONF_TIMEZONE,
    DOMAIN,
    NEXT_KEYS,
    PRAYER_KEYS,
    UPDATE_OK,
    UPDATE_RETRY,
    USER_AGENT,
)
from .parser import ParseError, parse_page

_LOGGER = logging.getLogger(__name__)


class FaziletCoordinator(DataUpdateCoordinator[dict[str, dict[str, str]]]):
    """Fetch times from Fazilet and keep a few days cached."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data[CONF_PATH]}",
            config_entry=entry,
            update_interval=UPDATE_OK,
        )
        self.path: str = entry.data[CONF_PATH]
        self.url = f"{BASE_URL}/{self.path}"
        self.tz = ZoneInfo(entry.data.get(CONF_TIMEZONE) or hass.config.time_zone)
        self._store: Store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self._unsub_tick = None

    # ---- helpers ---------------------------------------------------------
    def today(self) -> date:
        return dt_util.now(self.tz).date()

    def _prune(self, data: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        limit = (self.today() - timedelta(days=1)).isoformat()
        return {k: v for k, v in data.items() if k >= limit}

    def times_for(self, day: date) -> dict[str, datetime] | None:
        """Timezone-aware datetimes for one day (handles a midnight wrap)."""
        raw = (self.data or {}).get(day.isoformat())
        if not raw:
            return None
        result: dict[str, datetime] = {}
        prev: datetime | None = None
        offset = 0
        for key in PRAYER_KEYS:
            if key not in raw:
                continue
            hour, minute = (int(x) for x in raw[key].split(":"))
            dt = datetime(day.year, day.month, day.day, hour, minute, tzinfo=self.tz) + timedelta(days=offset)
            if prev is not None and dt <= prev:
                offset += 1
                dt += timedelta(days=1)
            result[key] = dt
            prev = dt
        return result

    def next_prayer(self) -> tuple[str, datetime] | None:
        now = dt_util.now(self.tz)
        best: tuple[str, datetime] | None = None
        for delta in (0, 1):
            times = self.times_for(now.date() + timedelta(days=delta))
            if not times:
                continue
            for key in NEXT_KEYS:
                dt = times.get(key)
                if dt and dt > now and (best is None or dt < best[1]):
                    best = (key, dt)
        return best

    # ---- fetching --------------------------------------------------------
    async def _async_update_data(self) -> dict[str, dict[str, str]]:
        cached = await self._store.async_load() or {}
        try:
            session = async_get_clientsession(self.hass)
            async with asyncio.timeout(30):
                resp = await session.get(
                    self.url, headers={"User-Agent": USER_AGENT, "Accept-Language": "tr"}
                )
                resp.raise_for_status()
                html = await resp.text()
            page = parse_page(html)
        except (aiohttp.ClientError, TimeoutError, ParseError) as err:
            self.update_interval = UPDATE_RETRY
            data = self._prune(dict(self.data or cached))
            if self.today().isoformat() in data:
                _LOGGER.warning("Fazilet update failed (%s); using cached times", err)
                return data
            raise UpdateFailed(f"Could not get times from {self.url}: {err}") from err

        for warning in page.warnings:
            _LOGGER.warning("Fazilet page %s: %s", self.path, warning)

        data = dict(self.data or cached)
        for day, times in page.days.items():
            data[day.isoformat()] = times
        data = self._prune(data)
        await self._store.async_save(data)

        if self.today().isoformat() in data:
            self.update_interval = UPDATE_OK
        else:
            _LOGGER.warning(
                "Fazilet page %s has no times for today (%s); retrying soon",
                self.path, self.today(),
            )
            self.update_interval = UPDATE_RETRY
        return data

    # ---- scheduled state refresh at every prayer time ---------------------
    @callback
    def async_start_ticks(self) -> None:
        self._schedule_tick()

    @callback
    def async_stop_ticks(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None

    @callback
    def _schedule_tick(self) -> None:
        now = dt_util.now(self.tz)
        candidates = [
            datetime.combine(now.date() + timedelta(days=1), time(0, 0, 5), tzinfo=self.tz)
        ]
        for delta in (0, 1):
            times = self.times_for(now.date() + timedelta(days=delta))
            if times:
                candidates += [t for t in times.values() if t > now]
        self._unsub_tick = async_track_point_in_utc_time(
            self.hass, self._tick, dt_util.as_utc(min(candidates))
        )

    async def _tick(self, _now: datetime) -> None:
        self._unsub_tick = None
        today = self.today()
        if not self.data or any(
            (today + timedelta(days=d)).isoformat() not in self.data for d in (0, 1)
        ):
            await self.async_request_refresh()
        self.async_update_listeners()
        self._schedule_tick()
