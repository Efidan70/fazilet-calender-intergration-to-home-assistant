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
- `Next prayer` (name, with today's times as attributes) and `Next prayer time`
- `Time until sahur` and `Time until iftar` (minutes, updated every minute). Sahur ends at İmsak and iftar is at Akşam, as in the Fazilet imsakiye.
- A calendar with today's and tomorrow's prayer times
- An event entity `Prayer` that fires at every prayer time, and optionally a reminder before it
- A diagnostic `Last update` sensor, downloadable diagnostics, and a repair notice if updates keep failing
- A Lovelace card

### Play the ezan or send a notification

Import the blueprint, then choose the prayers and the actions to run (media player, notification, lights, ...):

[![Import the blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FEfidan70%2Ffazilet-calender-intergration-to-home-assistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Ffazilet_takvimi%2Fprayer_actions.yaml)

To get a reminder before each prayer, open the integration → Configure and set the minutes. Then choose *Reminder* in the blueprint.

You can also write your own automation on the bus event `fazilet_takvimi_event`. Its data contains `kind` (`prayer_time` or `reminder`), `prayer` (`imsak`, `sabah`, `gunes`, `ogle`, `ikindi`, `aksam`, `yatsi`), `prayer_name`, `time`, `title` and `path`.

### Lovelace card

The card is served by the integration, so no extra resource is needed (reload the browser after the first install):

```yaml
type: custom:fazilet-card
entity: sensor.<your_city>_next_prayer
show_sabah: false   # optional
title: My city      # optional
```

Check the entity ID under Settings → Entities, it depends on the name you chose during setup.

## Why the times are correct

- Nothing is calculated. The times are taken exactly as published on the Fazilet page.
- Each day is stored under the date the page itself reports (yesterday/today/tomorrow), so an outdated page is never used as today.
- Incomplete times or times in the wrong order are rejected. The last known good times stay in place and a warning is written to the log.
- Refresh every 6 hours, and every 30 minutes while today's times are missing.

## Limitations

- Fazilet has no official API. If the website changes, the parser may need an update.
- Religious days (kandil, bayram) and Hijri dates are not included yet.

## Tests

`python3 -I tests/test_parser.py`
