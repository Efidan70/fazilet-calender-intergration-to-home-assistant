"""Fazilet Takvimi prayer times for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

import homeassistant.helpers.config_validation as cv
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, DOMAIN
from .coordinator import FaziletCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR, Platform.EVENT]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type FaziletConfigEntry = ConfigEntry[FaziletCoordinator]


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Fazilet Takvimi",
        entry_type=DeviceEntryType.SERVICE,
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve and register the optional Lovelace card (never blocks setup)."""
    try:
        from homeassistant.components.frontend import add_extra_js_url

        card = Path(__file__).parent / "www" / "fazilet-card.js"
        await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
        add_extra_js_url(hass, CARD_URL)
    except Exception:  # noqa: BLE001 - the card is optional
        _LOGGER.warning("Could not register the Fazilet Lovelace card", exc_info=True)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FaziletConfigEntry) -> bool:
    coordinator = FaziletCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_ticks()
    entry.async_on_unload(coordinator.async_stop_ticks)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: FaziletConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FaziletConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
