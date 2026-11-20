"""Calendar entity listing the daily prayer times."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import FaziletConfigEntry, device_info
from .const import PRAYER_KEYS, PRAYER_NAMES
from .coordinator import FaziletCoordinator

EVENT_LENGTH = timedelta(minutes=15)


async def async_setup_entry(
    hass: HomeAssistant, entry: FaziletConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([FaziletCalendar(entry.runtime_data, entry)])


class FaziletCalendar(CoordinatorEntity[FaziletCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Vakitler"
    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator: FaziletCoordinator, entry: FaziletConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = device_info(entry)

    def _events_for(self, day: date) -> list[CalendarEvent]:
        times = self.coordinator.times_for(day)
        if not times:
            return []
        return [
            CalendarEvent(start=dt, end=dt + EVENT_LENGTH, summary=PRAYER_NAMES[key])
            for key in PRAYER_KEYS
            if (dt := times.get(key))
        ]

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now(self.coordinator.tz)
        for delta in (0, 1):
            for ev in self._events_for(now.date() + timedelta(days=delta)):
                if ev.end > now:
                    return ev
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        day = start_date.astimezone(self.coordinator.tz).date() - timedelta(days=1)
        last = end_date.astimezone(self.coordinator.tz).date()
        while day <= last:
            events += [e for e in self._events_for(day) if e.end > start_date and e.start < end_date]
            day += timedelta(days=1)
        return sorted(events, key=lambda e: e.start)
