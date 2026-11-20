"""Fazilet Takvimi prayer times for Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN
from .coordinator import FaziletCoordinator

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]

type FaziletConfigEntry = ConfigEntry[FaziletCoordinator]


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Fazilet Takvimi",
        entry_type=DeviceEntryType.SERVICE,
    )


async def async_setup_entry(hass: HomeAssistant, entry: FaziletConfigEntry) -> bool:
    coordinator = FaziletCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_ticks()
    entry.async_on_unload(coordinator.async_stop_ticks)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FaziletConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
