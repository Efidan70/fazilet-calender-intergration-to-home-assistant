"""Run: python3 -I tests/test_logic.py"""
import importlib
import pathlib
import sys
import types
import unittest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# Load the package WITHOUT running its __init__ (that needs Home Assistant).
_dir = pathlib.Path(__file__).parent.parent / "custom_components/fazilet_takvimi"
_pkg = types.ModuleType("fz_pkg")
_pkg.__path__ = [str(_dir)]
sys.modules["fz_pkg"] = _pkg
logic = importlib.import_module("fz_pkg.logic")

TZ = ZoneInfo("Europe/Amsterdam")
DAY1 = {"imsak": "05:52", "sabah": "06:12", "gunes": "07:58", "ogle": "12:28",
        "ikindi": "14:25", "aksam": "16:48", "yatsi": "18:37"}
DAY2 = {"imsak": "05:53", "sabah": "06:13", "gunes": "07:59", "ogle": "12:28",
        "ikindi": "14:24", "aksam": "16:46", "yatsi": "18:36"}
RAW = {date(2026, 11, 20): DAY1, date(2026, 11, 21): DAY2}


def get_times(day):
    return logic.resolve_day(RAW.get(day), day, TZ)


def at(h, m, s=0, d=20):
    return datetime(2026, 11, d, h, m, s, tzinfo=TZ)


class LogicTests(unittest.TestCase):
    def test_next_prayer(self):
        self.assertEqual(logic.next_prayer(get_times, at(13, 0))[0], "ikindi")
        self.assertEqual(logic.next_prayer(get_times, at(19, 0))[0], "imsak")  # tomorrow
        self.assertEqual(logic.next_prayer(get_times, at(19, 0))[1], at(5, 53, d=21))

    def test_next_prayer_skips_sabah(self):
        self.assertEqual(logic.next_prayer(get_times, at(5, 59))[0], "gunes")

    def test_countdown_rounds_up(self):
        self.assertEqual(logic.minutes_until(get_times, at(16, 0), "aksam"), 48)
        self.assertEqual(logic.minutes_until(get_times, at(16, 47, 30), "aksam"), 1)
        # after iftar the next one is tomorrow's (23h46m later)
        self.assertEqual(logic.minutes_until(get_times, at(17, 0), "aksam"), 23 * 60 + 46)

    def test_due_events_fire_once(self):
        fired = set()
        due = logic.due_events(get_times, at(12, 28, 2), 0, fired)
        self.assertEqual([(k, key) for k, key, _ in due], [("prayer_time", "ogle")])
        for kind, key, when in due:
            fired.add((kind, key, when.isoformat()))
        self.assertEqual(logic.due_events(get_times, at(12, 29), 0, fired), [])

    def test_late_tick_still_fires_within_lookback(self):
        self.assertEqual(len(logic.due_events(get_times, at(12, 31), 0, set())), 1)
        self.assertEqual(len(logic.due_events(get_times, at(12, 40), 0, set())), 0)

    def test_reminder(self):
        due = logic.due_events(get_times, at(12, 18, 1), 10, set())
        self.assertEqual([(k, key) for k, key, _ in due], [("reminder", "ogle")])

    def test_next_wakeup(self):
        self.assertEqual(logic.next_wakeup(get_times, at(13, 0), 0), at(14, 25))
        self.assertEqual(logic.next_wakeup(get_times, at(13, 0), 10), at(14, 15))
        # after the last prayer: tomorrow's imsak is not known yet beyond day 2 -> midnight/imsak
        self.assertEqual(logic.next_wakeup(get_times, at(19, 0), 0), at(0, 0, 5, d=21))

    def test_midnight_wrap(self):
        raw = {"imsak": "01:10", "sabah": "01:40", "gunes": "04:30", "ogle": "13:40",
               "ikindi": "18:20", "aksam": "22:50", "yatsi": "00:35"}
        times = logic.resolve_day(raw, date(2026, 6, 20), TZ)
        self.assertEqual(times["yatsi"], datetime(2026, 6, 21, 0, 35, tzinfo=TZ))

    def test_missing_day(self):
        self.assertIsNone(get_times(date(2026, 11, 25)))
        self.assertIsNone(logic.next_prayer(lambda d: None, at(10, 0)))


if __name__ == "__main__":
    unittest.main()
