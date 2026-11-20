"""Sensors for Fazilet Takvimi."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FaziletConfigEntry, device_info
from .const import PRAYER_KEYS, PRAYER_NAMES
from .coordinator import FaziletCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: FaziletConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [FaziletTimeSensor(coordinator, entry, k) for k in PRAYER_KEYS]
    entities += [FaziletNextName(coordinator, entry), FaziletNextTime(coordinator, entry)]
    async_add_entities(entities)


class _Base(CoordinatorEntity[FaziletCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FaziletCoordinator, entry: FaziletConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = device_info(entry)


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
            "time": value.strftime("%H:%M") if value else None,
            "date": self.coordinator.today().isoformat(),
            "source": self.coordinator.url,
        }

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None


class FaziletNextName(_Base):
    _attr_name = "Volgende vakit"
    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "next_prayer")

    @property
    def native_value(self) -> str | None:
        nxt = self.coordinator.next_prayer()
        return PRAYER_NAMES[nxt[0]] if nxt else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        nxt = self.coordinator.next_prayer()
        return {"time": nxt[1].isoformat() if nxt else None, "key": nxt[0] if nxt else None}


class FaziletNextTime(_Base):
    _attr_name = "Volgende vakit tijd"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "next_prayer_time")

    @property
    def native_value(self) -> datetime | None:
        nxt = self.coordinator.next_prayer()
        return nxt[1] if nxt else None
