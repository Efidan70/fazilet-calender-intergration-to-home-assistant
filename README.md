# Fazilet Takvimi voor Home Assistant

Gebedstijden rechtstreeks van [namaz-vakitleri.fazilettakvimi.com](https://namaz-vakitleri.fazilettakvimi.com), dus dezelfde tijden als in de Fazilet Takvimi. Werkt voor elke stad die Fazilet toont (Nederland, Duitsland, Turkije, ...).

Prayer times taken straight from the Fazilet Takvimi website, for any city it lists.

[![Open je Home Assistant en voeg deze repository toe aan HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Efidan70&repository=fazilet-calender-intergration-to-home-assistant&category=integration)
[![Start de configuratie van de integratie.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=fazilet_takvimi)

## Installeren / Install

1. HACS → ⋮ → Custom repositories → `https://github.com/Efidan70/fazilet-calender-intergration-to-home-assistant`, type *Integration* → Download. Of kopieer `custom_components/fazilet_takvimi` naar je `config/custom_components/`.
2. Herstart Home Assistant.
3. Instellingen → Apparaten & diensten → Integratie toevoegen → **Fazilet Takvimi**.
4. Kies land en stad (bijv. Hollanda → Venlo), of voer het pad in: `hollanda/venlo`.
5. Kies de tijdzone van de stad (standaard die van je Home Assistant).

## Wat je krijgt

- Sensoren (tijdstempel): İmsak, Sabah, Güneş, Öğle, İkindi, Akşam, Yatsı
- `Volgende vakit` (naam) en `Volgende vakit tijd`
- Agenda `Vakitler` met alle tijden van vandaag en morgen

Voorbeeld-automatisering (Akşam). De entiteitsnaam hangt af van de naam die je bij het instellen kiest, controleer hem onder Instellingen → Entiteiten:

```yaml
trigger:
  - platform: time
    at: sensor.venlo_hollanda_aksam
action:
  - service: notify.notify
    data: { message: "Akşam vakti girdi" }
```

## Waarom de tijden kloppen

- Er wordt niets berekend: de tijden komen letterlijk van de Fazilet-pagina.
- Elke dag wordt opgeslagen onder de datum die de pagina zelf noemt (gisteren/vandaag/morgen), dus een verouderde pagina wordt nooit als vandaag gebruikt.
- Tijden die niet volledig zijn of in verkeerde volgorde staan worden geweigerd; dan blijven de laatst bekende tijden staan en staat er een waarschuwing in het log.
- Verversing elke 6 uur, elke 30 minuten zolang de tijden van vandaag ontbreken.

## Beperkingen

- Fazilet heeft geen officiële API; als de website verandert, kan de parser aangepast moeten worden.
- Dinî günler/kandil-dagen zitten er nog niet in.

## Tests

`python3 -I tests/test_parser.py`
