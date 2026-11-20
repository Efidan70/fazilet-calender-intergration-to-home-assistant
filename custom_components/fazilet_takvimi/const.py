"""Constants for Fazilet Takvimi."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "fazilet_takvimi"
BASE_HOST = "namaz-vakitleri.fazilettakvimi.com"
BASE_URL = f"https://{BASE_HOST}"

CONF_PATH = "path"
CONF_TIMEZONE = "timezone"
CONF_NAME = "name"

PRAYER_KEYS = ("imsak", "sabah", "gunes", "ogle", "ikindi", "aksam", "yatsi")
PRAYER_NAMES = {
    "imsak": "İmsak",
    "sabah": "Sabah",
    "gunes": "Güneş",
    "ogle": "Öğle",
    "ikindi": "İkindi",
    "aksam": "Akşam",
    "yatsi": "Yatsı",
}
# Prayers used for "next prayer" (Sabah is a sub-time of the Imsak period).
NEXT_KEYS = ("imsak", "gunes", "ogle", "ikindi", "aksam", "yatsi")

UPDATE_OK = timedelta(hours=6)
UPDATE_RETRY = timedelta(minutes=30)
USER_AGENT = "HomeAssistant-FaziletTakvimi/0.1"
