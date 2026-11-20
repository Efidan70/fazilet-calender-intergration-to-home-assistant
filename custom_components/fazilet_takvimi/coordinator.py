"""Data coordinator for Fazilet Takvimi."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import logic
from .const import (
    BASE_URL,
    CONF_PATH,
    CONF_REMINDER,
    CONF_TIMEZONE,
    DOMAIN,
    EVENT_NAME,
    PRAYER_NAMES,
    UPDATE_OK,
    UPDATE_RETRY,
    USER_AGENT,
)
from .parser import ParseError, parse_page

_LOGGER = logging.getLogger(__name__)

ISSUE_AFTER_FAILURES = 6  # ~3 hours of failed retries


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
        self.entry = entry
        self.path: str = entry.data[CONF_PATH]
        self.url = f"{BASE_URL}/{self.path}"
        opts = {**entry.data, **entry.options}
        self.tz = ZoneInfo(opts.get(CONF_TIMEZONE) or hass.config.time_zone)
        self.reminder_minutes: int = int(opts.get(CONF_REMINDER, 0) or 0)
        self._store: Store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self._unsub_tick = None
        self._unsub_minute = None
        self._fired: set[tuple[str, str, str]] = set()
        self._prayer_listeners: list[Callable[[str, str, datetime], None]] = []
        # diagnostics
        self.last_success: datetime | None = None
        self.last_error: str | None = None
        self.warnings: list[str] = []
        self.fail_count = 0

    # ---- helpers ---------------------------------------------------------
    def now(self) -> datetime:
        return dt_util.now(self.tz)

    def today(self) -> date:
        return self.now().date()

    def _prune(self, data: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        limit = (self.today() - timedelta(days=1)).isoformat()
        return {k: v for k, v in data.items() if k >= limit}

    def times_for(self, day: date) -> dict[str, datetime] | None:
        return logic.resolve_day((self.data or {}).get(day.isoformat()), day, self.tz)

    def next_prayer(self) -> tuple[str, datetime] | None:
        return logic.next_prayer(self.times_for, self.now())

    def minutes_until(self, key: str) -> int | None:
        return logic.minutes_until(self.times_for, self.now(), key)

    # ---- fetching --------------------------------------------------------
    def _record_failure(self, err: Exception) -> None:
        self.fail_count += 1
        self.last_error = f"{type(err).__name__}: {err}"
        if self.fail_count >= ISSUE_AFTER_FAILURES:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"update_failing_{self.entry.entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="update_failing",
                translation_placeholders={"name": self.entry.title, "url": self.url},
            )

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
            self._record_failure(err)
            data = self._prune(dict(self.data or cached))
            if self.today().isoformat() in data:
                _LOGGER.warning("Fazilet update failed (%s); using cached times", err)
                return data
            raise UpdateFailed(f"Could not get times from {self.url}: {err}") from err

        self.warnings = list(page.warnings)
        for warning in page.warnings:
            _LOGGER.warning("Fazilet page %s: %s", self.path, warning)

        data = dict(self.data or cached)
        for day, times in page.days.items():
            data[day.isoformat()] = times
        data = self._prune(data)
        await self._store.async_save(data)

        self.last_success = dt_util.utcnow()
        self.last_error = None
        self.fail_count = 0
        ir.async_delete_issue(self.hass, DOMAIN, f"update_failing_{self.entry.entry_id}")

        if self.today().isoformat() in data:
            self.update_interval = UPDATE_OK
        else:
            _LOGGER.warning(
                "Fazilet page %s has no times for today (%s); retrying soon",
                self.path, self.today(),
            )
            self.update_interval = UPDATE_RETRY
        return data

    # ---- prayer events -----------------------------------------------------
    @callback
    def async_add_prayer_listener(self, cb: Callable[[str, str, datetime], None]) -> Callable[[], None]:
        self._prayer_listeners.append(cb)

        @callback
        def _remove() -> None:
            if cb in self._prayer_listeners:
                self._prayer_listeners.remove(cb)

        return _remove

    @callback
    def _fire_due_events(self) -> None:
        now = self.now()
        for kind, key, when in logic.due_events(self.times_for, now, self.reminder_minutes, self._fired):
            self._fired.add((kind, key, when.isoformat()))
            self.hass.bus.async_fire(
                EVENT_NAME,
                {
                    "entry_id": self.entry.entry_id,
                    "title": self.entry.title,
                    "path": self.path,
                    "kind": kind,
                    "prayer": key,
                    "prayer_name": PRAYER_NAMES[key],
                    "time": when.isoformat(),
                },
            )
            for listener in list(self._prayer_listeners):
                listener(kind, key, when)
        cutoff = (now - timedelta(days=2)).isoformat()
        self._fired = {m for m in self._fired if m[2] >= cutoff}

    # ---- scheduling ---------------------------------------------------------
    @callback
    def async_start_ticks(self) -> None:
        self._schedule_tick()
        # Countdown sensors change every minute.
        self._unsub_minute = async_track_time_change(
            self.hass, lambda _now: self.async_update_listeners(), second=0
        )

    @callback
    def async_stop_ticks(self) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None
        if self._unsub_minute:
            self._unsub_minute()
            self._unsub_minute = None

    @callback
    def _schedule_tick(self) -> None:
        wake = logic.next_wakeup(self.times_for, self.now(), self.reminder_minutes)
        self._unsub_tick = async_track_point_in_utc_time(self.hass, self._tick, dt_util.as_utc(wake))

    async def _tick(self, _now: datetime) -> None:
        self._unsub_tick = None
        today = self.today()
        if not self.data or any(
            (today + timedelta(days=d)).isoformat() not in self.data for d in (0, 1)
        ):
            await self.async_request_refresh()
        self._fire_due_events()
        self.async_update_listeners()
        self._schedule_tick()
