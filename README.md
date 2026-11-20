# Fazilet Takvimi for Home Assistant

[![Add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Efidan70&repository=fazilet-calender-intergration-to-home-assistant&category=integration)
[![Start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=fazilet_takvimi)

Prayer times taken straight from [namaz-vakitleri.fazilettakvimi.com](https://namaz-vakitleri.fazilettakvimi.com), so you get the same times as in the Fazilet Takvimi. Works for every city the site lists, in any country.

## Installation

1. Click the first button above, or in HACS go to ⋮ → Custom repositories, add `https://github.com/Efidan70/fazilet-calender-intergration-to-home-assistant` as type *Integration*, then Download. You can also copy `custom_components/fazilet_takvimi` into your `config/custom_components/` folder.
2. Restart Home Assistant.
3. Go to Settings → Devices & services → Add integration → **Fazilet Takvimi** (or use the second button).
4. Pick your country and city from the list, or enter the page path yourself. The path is the part of the Fazilet URL after the domain, for example `almanya/koln` (country/city).
5. Choose the time zone of the city (defaults to your Home Assistant time zone).

## What you get

- Timestamp sensors: İmsak, Sabah, Güneş, Öğle, İkindi, Akşam, Yatsı
- `Next prayer` (name) and `Next prayer time` sensors
- A calendar with today's and tomorrow's prayer times

Example automation (Akşam). The entity ID depends on the name you chose during setup, so check it under Settings → Entities:

```yaml
trigger:
  - platform: time
    at: sensor.<your_city>_aksam
action:
  - service: notify.notify
    data: { message: "Akşam time has started" }
```

## Why the times are correct

- Nothing is calculated. The times are taken exactly as published on the Fazilet page.
- Each day is stored under the date the page itself reports (yesterday/today/tomorrow), so an outdated page is never used as today.
- Incomplete times or times in the wrong order are rejected. The last known good times stay in place and a warning is written to the log.
- Refresh every 6 hours, and every 30 minutes while today's times are missing.

## Limitations

- Fazilet has no official API. If the website changes, the parser may need an update.
- Religious days (kandil etc.) are not included yet.

## Tests

`python3 -I tests/test_parser.py`
