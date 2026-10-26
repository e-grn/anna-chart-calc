"""Transits of the slow planets to a natal chart over a period of years -> transits.json.

periods: [start "YYYY-MM", end "YYYY-MM", transiting planet, aspect, natal point], hits closer than
`merge_gap_days` merged into one period. ingress: [date, planet, natal house, sign] when a transiting planet
enters another natal house. Same algorithm and format as the Anna Birth Chart reference transits.
"""
from __future__ import annotations

import datetime as dt

import swisseph as swe

from .ephemeris import init_ephemeris
from .natal import SIGNS, house_of


def default_range(years: int, today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    y = (today or dt.date.today()).year
    return dt.date(y, 1, 1), dt.date(y + years - 1, 12, 31)


def transits(chart: dict, lat: float | None, lon: float | None, settings: dict,
             start: dt.date, end: dt.date) -> dict:
    init_ephemeris()
    ts = settings["transits"]
    natal = {k: v["lon"] for k, v in chart["planets"].items() if k not in ts["exclude_natal"]}
    cusps = None
    if chart.get("asc") is not None:
        if lat is None or lon is None:
            raise ValueError("coordinates are needed to compute house cusps")
        cusps, ascmc = swe.houses(chart["jd"], lat, lon, settings["house_system"].encode())
        natal["ASC"], natal["MC"] = ascmc[0], ascmc[1]
        natal["DSC"], natal["IC"] = (ascmc[0] + 180) % 360, (ascmc[1] + 180) % 360
    planets = [(n, getattr(swe, c)) for n, c in ts["planets"]]
    skip = {k: set(v) for k, v in ts["skip"].items()}
    orb, step, gap = ts["orb"], dt.timedelta(days=ts["step_days"]), ts["merge_gap_days"]

    hits: dict[tuple, list[dt.date]] = {}
    ingress, prev_house = [], {}
    d = start
    while d <= end:
        jd = swe.julday(d.year, d.month, d.day, 0)
        for name, const in planets:
            lon_t = swe.calc_ut(jd, const)[0][0]
            if cusps:
                h = house_of(lon_t, cusps)
                if prev_house.get(name) != h:
                    ingress.append((d.isoformat(), name, h, SIGNS[int(lon_t // 30)]))
                    prev_house[name] = h
            for nn, nl in natal.items():
                dd = abs((lon_t - nl + 180) % 360 - 180)
                for an, ang in ts["aspects"].items():
                    if an in skip.get(name, ()):
                        continue
                    if abs(dd - ang) <= orb:
                        hits.setdefault((name, an, nn), []).append(d)
        d += step

    periods = []
    for k, ds in hits.items():
        ds.sort()
        s = p = ds[0]
        for x in [*ds[1:], None]:
            if x is None or (x - p).days > gap:
                periods.append((s.isoformat()[:7], p.isoformat()[:7], *k))
                if x:
                    s = x
            if x:
                p = x
    periods.sort()
    return {"periods": periods, "ingress": ingress}
