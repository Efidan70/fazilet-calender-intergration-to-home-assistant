# Changelog

## 0.2.0
- Event entity `Prayer`: fires `prayer_time` and optional `reminder` events, plus a `fazilet_takvimi_event` event on the Home Assistant bus.
- Blueprint to run your own actions (ezan on a speaker, notification, ...) at prayer time.
- Options: change time zone and set a reminder (minutes before) after setup.
- Sensors: `Time until sahur`, `Time until iftar`, diagnostic `Last update`.
- Repair issue when updates keep failing, and config-entry diagnostics.
- Lovelace card `custom:fazilet-card`, served by the integration.
- Logic moved to a pure module with unit tests.

## 0.1.0
- First release: prayer-time sensors, next prayer, calendar, city picker for any location on the site.
