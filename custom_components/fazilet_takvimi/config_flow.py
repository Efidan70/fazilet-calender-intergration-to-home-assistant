"""Config flow: pick any country/city from Fazilet, or type a path."""
from __future__ import annotations

import asyncio
import re
import zoneinfo
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util

from .const import (
    BASE_HOST,
    BASE_URL,
    CONF_NAME,
    CONF_PATH,
    CONF_REMINDER,
    CONF_TIMEZONE,
    DOMAIN,
    USER_AGENT,
)
from .parser import ParseError, extract_links, parse_page


def _select(options: list[tuple[str, str]]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[SelectOptionDict(value=v, label=l) for v, l in options],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _clean_path(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^https?://[^/]+", "", value)
    return value.split("?")[0].split("#")[0].strip("/").lower()


class FaziletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FaziletOptionsFlow()

    def __init__(self) -> None:
        self._region: str | None = None
        self._region_label: str = ""
        self._regions: dict[str, str] = {}
        self._path: str = ""
        self._title: str = ""

    async def _fetch(self, path: str) -> str:
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(30):
            resp = await session.get(
                f"{BASE_URL}/{path}".rstrip("/"),
                headers={"User-Agent": USER_AGENT, "Accept-Language": "tr"},
            )
            resp.raise_for_status()
            return await resp.text()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["browse", "manual"])

    # ---- browse: region (country / Turkish province) -> place -------------
    async def async_step_browse(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._region = user_input["region"]
            self._region_label = self._regions.get(self._region, self._region)
            return await self.async_step_place()
        try:
            html = await self._fetch("")
        except (aiohttp.ClientError, TimeoutError):
            return self.async_show_form(step_id="manual", errors={"base": "cannot_connect"},
                                        data_schema=vol.Schema({vol.Required(CONF_PATH): str}))
        links = [(p, l) for p, l in extract_links(html, BASE_HOST) if "/" not in p]
        if not links:
            return await self.async_step_manual()
        self._regions = dict(links)
        return self.async_show_form(
            step_id="browse",
            data_schema=vol.Schema({vol.Required("region"): _select(links)}),
        )

    async def async_step_place(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._region
        if user_input is not None:
            self._path = _clean_path(user_input["place"])
            return await self.async_step_confirm()
        try:
            html = await self._fetch(self._region)
        except (aiohttp.ClientError, TimeoutError):
            return await self.async_step_manual()
        found = extract_links(html, BASE_HOST)
        links = [(p, l) for p, l in found if p.startswith(f"{self._region}/")]
        if not links:  # e.g. Turkey: provinces are root-level pages
            links = [(p, l) for p, l in found if "/" not in p and p != self._region]
        options = [(self._region, f"{self._region_label} ({self._region})")] + links
        return self.async_show_form(
            step_id="place",
            data_schema=vol.Schema({vol.Required("place"): _select(options)}),
        )

    # ---- manual path -------------------------------------------------------
    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._path = _clean_path(user_input[CONF_PATH])
            return await self.async_step_confirm()
        return self.async_show_form(
            step_id="manual", data_schema=vol.Schema({vol.Required(CONF_PATH): str})
        )

    # ---- validate + timezone ------------------------------------------------
    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(self._path)
            self._abort_if_unique_id_configured()
            if dt_util.get_time_zone(user_input[CONF_TIMEZONE]) is None:
                errors[CONF_TIMEZONE] = "bad_timezone"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={CONF_PATH: self._path, CONF_TIMEZONE: user_input[CONF_TIMEZONE]},
                )
        elif not self._title:
            try:
                page = parse_page(await self._fetch(self._path))
            except (aiohttp.ClientError, TimeoutError):
                return self.async_show_form(
                    step_id="manual", errors={"base": "cannot_connect"},
                    data_schema=vol.Schema({vol.Required(CONF_PATH, default=self._path): str}),
                )
            except ParseError:
                return self.async_show_form(
                    step_id="manual", errors={"base": "cannot_parse"},
                    data_schema=vol.Schema({vol.Required(CONF_PATH, default=self._path): str}),
                )
            title = page.title or self._path
            title = re.sub(r"\s*\|\s*Fazilet Takvimi.*$", "", title)
            self._title = title.replace(" Namaz Vakitleri", "").strip() or self._path

        zones = sorted(await self.hass.async_add_executor_job(zoneinfo.available_timezones))
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=self._title): str,
                vol.Required(CONF_TIMEZONE, default=self.hass.config.time_zone): SelectSelector(
                    SelectSelectorConfig(options=zones, mode=SelectSelectorMode.DROPDOWN)
                ),
            }
        )
        return self.async_show_form(step_id="confirm", data_schema=schema, errors=errors)


class FaziletOptionsFlow(OptionsFlow):
    """Change time zone and reminder after setup."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            if dt_util.get_time_zone(user_input[CONF_TIMEZONE]) is None:
                errors[CONF_TIMEZONE] = "bad_timezone"
            else:
                user_input[CONF_REMINDER] = int(user_input[CONF_REMINDER])
                return self.async_create_entry(data=user_input)
        zones = sorted(await self.hass.async_add_executor_job(zoneinfo.available_timezones))
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TIMEZONE, default=current.get(CONF_TIMEZONE) or self.hass.config.time_zone
                ): SelectSelector(SelectSelectorConfig(options=zones, mode=SelectSelectorMode.DROPDOWN)),
                vol.Required(CONF_REMINDER, default=int(current.get(CONF_REMINDER, 0) or 0)): NumberSelector(
                    NumberSelectorConfig(min=0, max=120, step=1, unit_of_measurement="min",
                                         mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
