"""Pure scheduling logic (no Home Assistant imports) so it can be unit-tested."""
from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, tzinfo

from .const import NEXT_KEYS, PRAYER_KEYS

GetTimes = Callable[[date], "dict[str, datetime] | None"]

LOOKBACK = timedelta(minutes=5)


def resolve_day(raw: dict[str, str] | None, day: date, tz: tzinfo) -> dict[str, datetime] | None:
    """Turn {'imsak': '05:52'} into aware datetimes; a time earlier than the
    previous one (e.g. Yatsı after midnight) rolls over to the next day."""
    if not raw:
        return None
    result: dict[str, datetime] = {}
    prev: datetime | None = None
    offset = 0
    for key in PRAYER_KEYS:
        if key not in raw:
            continue
        hour, minute = (int(x) for x in raw[key].split(":"))
        dt = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz) + timedelta(days=offset)
        if prev is not None and dt <= prev:
            offset += 1
            dt += timedelta(days=1)
        result[key] = dt
        prev = dt
    return result


def next_prayer(get_times: GetTimes, now: datetime) -> tuple[str, datetime] | None:
    best: tuple[str, datetime] | None = None
    for delta in (0, 1):
        times = get_times(now.date() + timedelta(days=delta))
        if not times:
            continue
        for key in NEXT_KEYS:
            dt = times.get(key)
            if dt and dt > now and (best is None or dt < best[1]):
                best = (key, dt)
    return best


def next_occurrence(get_times: GetTimes, now: datetime, key: str) -> datetime | None:
    best: datetime | None = None
    for delta in (0, 1):
        times = get_times(now.date() + timedelta(days=delta))
        dt = times.get(key) if times else None
        if dt and dt > now and (best is None or dt < best):
            best = dt
    return best


def minutes_until(get_times: GetTimes, now: datetime, key: str) -> int | None:
    """Whole minutes (rounded up) until the next occurrence of ``key``."""
    dt = next_occurrence(get_times, now, key)
    if dt is None:
        return None
    return max(0, math.ceil((dt - now).total_seconds() / 60))


def _scheduled(get_times: GetTimes, now: datetime, reminder_minutes: int):
    """Yield (kind, key, when) for yesterday..tomorrow."""
    for delta in (-1, 0, 1):
        times = get_times(now.date() + timedelta(days=delta))
        if not times:
            continue
        for key, dt in times.items():
            yield "prayer_time", key, dt
            if reminder_minutes > 0:
                yield "reminder", key, dt - timedelta(minutes=reminder_minutes)


def due_events(
    get_times: GetTimes,
    now: datetime,
    reminder_minutes: int,
    fired: set[tuple[str, str, str]],
) -> list[tuple[str, str, datetime]]:
    """Events that should have fired in the last LOOKBACK and have not yet."""
    out = []
    for kind, key, when in _scheduled(get_times, now, reminder_minutes):
        marker = (kind, key, when.isoformat())
        if now - LOOKBACK < when <= now and marker not in fired:
            out.append((kind, key, when))
    return sorted(out, key=lambda e: e[2])


def next_wakeup(get_times: GetTimes, now: datetime, reminder_minutes: int) -> datetime:
    """Next moment something changes: a prayer, a reminder, or just after midnight."""
    midnight = datetime.combine(now.date() + timedelta(days=1), time(0, 0, 5), tzinfo=now.tzinfo)
    candidates = [midnight]
    candidates += [w for _, _, w in _scheduled(get_times, now, reminder_minutes) if w > now]
    return min(candidates)
