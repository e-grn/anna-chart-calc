# anna-chart-calc

Natal chart and transit calculation used by [Anna Birth Chart](https://annabirthchart.com).

- **Swiss Ephemeris** (via [pyswisseph](https://github.com/astrorigin/pyswisseph)), tropical zodiac, Placidus houses by default.
- **Historical time zones.** The birth place's IANA time zone is found from its coordinates, and the UTC offset in force on the birth date is applied. This covers summer time and historical changes, for example Moscow time in Soviet Ukraine until 1990, or no daylight saving in Indiana until 2006.
- **Clock changes.** A local time that never existed (clocks went forward) or happened twice (clocks went back) is reported, not guessed, so the caller can ask the user.
- **Birth time unknown.** The chart is calculated for local noon, without houses, ASC or MC.

Output is two JSON files: `chart.json` (positions, houses, aspects) and `transits.json` (slow-planet transits and house ingresses over a period of years).

## Licence

GNU Affero General Public License v3.0 (see [LICENSE](LICENSE)). Swiss Ephemeris is © Astrodienst AG and is used here under its AGPL licence option. The bundled ephemeris files `sepl_18.se1`, `semo_18.se1` and `seas_18.se1` (years 1800–2399) are from [aloistr/swisseph](https://github.com/aloistr/swisseph).

The Anna Birth Chart book generator runs this module as a separate program and exchanges data with it through the command line and JSON files.

## Install

Python 3.10–3.12.

```bash
uv venv && uv pip install -e ".[dev]"
```

## Usage

```bash
# What UTC offset applied to this local time and place?
anna-chart-calc resolve-time --date 1985-07-15 --time 12:00 --lat 50.4547 --lon 30.5239
#  -> {"tz": "Europe/Kyiv", "utc_offset": "+04:00", "utc": "1985-07-15T08:00:00+00:00", "status": "ok", ...}

anna-chart-calc chart --date 1990-07-04 --time 15:20 --lat 40.7128 --lon -74.006 --place "New York, USA" --out chart.json
anna-chart-calc chart --date 1990-07-04 --time-unknown --lat 40.7128 --lon -74.006 --out chart.json
anna-chart-calc transits --chart chart.json --start 2026-01-01 --end 2036-12-31 --out transits.json

# Both files from one input file
anna-chart-calc run birth.json --out-dir charts/order-123
```

`birth.json`:

```json
{"date": "1990-07-04", "time": "15:20", "lat": 40.7128, "lon": -74.006, "place": "New York, USA",
 "tz": null, "utc_offset": null, "ambiguous": "error", "nonexistent": "error",
 "transits": {"start": "2026-01-01", "end": "2036-12-31"}}
```

| Field | Meaning |
|---|---|
| `time` | Local clock time `HH:MM[:SS]`, or `null` if unknown |
| `lat`, `lon` | Decimal degrees, north and east positive |
| `tz` | Optional IANA zone. By default it is found from the coordinates |
| `utc_offset` | Optional fixed offset such as `+03:00`. Overrides the tz database (use it when the user knows the offset) |
| `ambiguous` | `error` (default), `earlier` or `later`, for a time that happened twice |
| `nonexistent` | `error` (default) or `forward` (02:30 on a spring-forward night becomes 03:30), for a time that never existed |

When the time is ambiguous or never existed and the policy is `error`, the program exits with code 2 and prints JSON to stderr:

```json
{"error": "ambiguous", "message": "...", "options": [{"choice": "earlier", "utc_offset": "-04:00", "utc": "..."}, {"choice": "later", ...}]}
```

## Settings

Planets, aspects, orbs, house system and transit parameters are in [`settings.json`](src/anna_chart_calc/settings.json). Override any of them with `--settings my.json`; top-level keys are merged.

## Accuracy notes

- Time zone history comes from the IANA tz database (`tzdata` package). It is reliable from 1970. Before 1970, places that now share a zone are assumed to have had the same clock rules; that is not always true, especially for local US daylight saving before 1967. If the user knows the offset, pass `utc_offset`.
- Positions in `chart.json` are truncated to whole arc-minutes in `pos` and rounded to 0.001° in `lon`.

## Tests

```bash
pytest -q
```

The tests use synthetic birth data only.
