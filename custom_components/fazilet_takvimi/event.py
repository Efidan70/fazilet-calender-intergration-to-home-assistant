"""Event entity that fires at every prayer time (and optional reminder)."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FaziletConfigEntry, device_info
from .const import PRAYER_NAMES


async def async_setup_entry(
    hass: HomeAssistant, entry: FaziletConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([FaziletPrayerEvent(entry)])


class FaziletPrayerEvent(EventEntity):
    """Fires `prayer_time` at the prayer and `reminder` N minutes before."""

    _attr_has_entity_name = True
    _attr_name = "Prayer"
    _attr_icon = "mdi:mosque"
    _attr_event_types = ["prayer_time", "reminder"]
    _attr_should_poll = False

    def __init__(self, entry: FaziletConfigEntry) -> None:
        self._coordinator = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_event"
        self._attr_device_info = device_info(entry)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._coordinator.async_add_prayer_listener(self._handle))

    @callback
    def _handle(self, kind: str, key: str, when: datetime) -> None:
        self._trigger_event(
            kind,
            {"prayer": key, "prayer_name": PRAYER_NAMES[key], "time": when.isoformat()},
        )
        self.async_write_ha_state()
