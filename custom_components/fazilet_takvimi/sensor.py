"""Sensors for Fazilet Takvimi."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FaziletConfigEntry, device_info
from .const import NEXT_KEYS, PRAYER_KEYS, PRAYER_NAMES
from .coordinator import FaziletCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: FaziletConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    c = entry.runtime_data
    entities: list[SensorEntity] = [FaziletTimeSensor(c, entry, k) for k in PRAYER_KEYS]
    entities += [
        FaziletNextName(c, entry),
        FaziletNextTime(c, entry),
        FaziletCountdown(c, entry, "imsak", "sahur", "Time until sahur"),
        FaziletCountdown(c, entry, "aksam", "iftar", "Time until iftar"),
        FaziletLastUpdate(c, entry),
    ]
    async_add_entities(entities)


class _Base(CoordinatorEntity[FaziletCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FaziletCoordinator, entry: FaziletConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = device_info(entry)
        self._entry = entry


class FaziletTimeSensor(_Base):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry, key: str) -> None:
        super().__init__(coordinator, entry, key)
        self._key = key
        self._attr_name = PRAYER_NAMES[key]

    @property
    def native_value(self) -> datetime | None:
        times = self.coordinator.times_for(self.coordinator.today())
        return times.get(self._key) if times else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        value = self.native_value
        return {
            "time": value.astimezone(self.coordinator.tz).strftime("%H:%M") if value else None,
            "date": self.coordinator.today().isoformat(),
            "source": self.coordinator.url,
        }

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None


class FaziletNextName(_Base):
    _attr_name = "Next prayer"
    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "next_prayer")

    @property
    def native_value(self) -> str | None:
        nxt = self.coordinator.next_prayer()
        return PRAYER_NAMES[nxt[0]] if nxt else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator
        nxt = c.next_prayer()
        times = c.times_for(c.today()) or {}
        return {
            "city": self._entry.title,
            "next_key": nxt[0] if nxt else None,
            "next_time": nxt[1].isoformat() if nxt else None,
            "today": {k: v.astimezone(c.tz).strftime("%H:%M") for k, v in times.items()},
        }


class FaziletNextTime(_Base):
    _attr_name = "Next prayer time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "next_prayer_time")

    @property
    def native_value(self) -> datetime | None:
        nxt = self.coordinator.next_prayer()
        return nxt[1] if nxt else None


class FaziletCountdown(_Base):
    """Minutes until sahur (İmsak) or iftar (Akşam)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, entry, key: str, suffix: str, name: str) -> None:
        super().__init__(coordinator, entry, suffix)
        self._key = key
        self._attr_name = name

    @property
    def native_value(self) -> int | None:
        return self.coordinator.minutes_until(self._key)


class FaziletLastUpdate(_Base):
    _attr_name = "Last update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "last_update")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator
        return {
            "source": c.url,
            "last_error": c.last_error,
            "failed_attempts": c.fail_count,
            "warnings": c.warnings,
            "days_cached": sorted(c.data or {}),
        }
