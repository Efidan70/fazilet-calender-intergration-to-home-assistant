"""Diagnostics for Fazilet Takvimi."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import FaziletConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FaziletConfigEntry
) -> dict[str, Any]:
    c = entry.runtime_data
    return {
        "path": c.path,
        "url": c.url,
        "timezone": str(c.tz),
        "reminder_minutes": c.reminder_minutes,
        "last_success": c.last_success.isoformat() if c.last_success else None,
        "last_error": c.last_error,
        "fail_count": c.fail_count,
        "warnings": c.warnings,
        "cached_days": c.data,
    }
