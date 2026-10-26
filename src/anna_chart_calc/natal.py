"""Natal chart: planet positions, houses (Placidus by default), aspects -> chart.json.

The output format and the formulas follow the Anna Birth Chart reference charts exactly
(positions truncated to whole arc-minutes in "pos", longitudes rounded to 0.001 deg in "lon").
"""
from __future__ import annotations

import datetime as dt

import swisseph as swe

from . import __version__
from .ephemeris import init_ephemeris
from .timeresolve import ResolvedTime

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def fmt(lon: float) -> str:
    return f"{int(lon % 30)}°{int((lon % 1) * 60):02d}' {SIGNS[int(lon // 30)]}"


def house_of(lon: float, cusps) -> int | None:
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if (lon - a) % 360 < (b - a) % 360:
            return i + 1
    return None


def julian_day_ut(utc: dt.datetime) -> float:
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    if utc.microsecond:
        hour += utc.microsecond / 3.6e9
    return swe.julday(utc.year, utc.month, utc.day, hour)


def aspects(lons: dict[str, float], settings: dict) -> list:
    asp, orbs = settings["natal_aspects"], settings["natal_orbs"]
    minor, minor_orb = set(settings["minor_points"]), settings["minor_point_orb"]
    names = list(lons)
    res = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            d = abs((lons[a] - lons[b] + 180) % 360 - 180)
            for name, ang in asp.items():
                orb = orbs[name] if a not in minor and b not in minor else minor_orb
                if abs(d - ang) <= orb:
                    res.append((a, name, b, round(abs(d - ang), 2)))
    return sorted(res, key=lambda x: x[3])


def natal_chart(t: ResolvedTime, lat: float, lon: float, settings: dict, time_known: bool = True,
                place: str | None = None) -> dict:
    init_ephemeris()
    jd = julian_day_ut(t.utc_datetime)
    out: dict = {"jd": jd}
    cusps = None
    if time_known:
        cusps, ascmc = swe.houses(jd, lat, lon, settings["house_system"].encode())
        out.update({"asc": fmt(ascmc[0]), "mc": fmt(ascmc[1]), "cusps": [fmt(c) for c in cusps]})
    else:
        out.update({"asc": None, "mc": None, "cusps": None})
    out["planets"] = {}
    lons: dict[str, float] = {}
    for name, const in settings["planets"]:
        r, _ = swe.calc_ut(jd, getattr(swe, const), swe.FLG_SWIEPH | swe.FLG_SPEED)
        lons[name] = r[0]
        out["planets"][name] = {"pos": fmt(r[0]), "lon": round(r[0], 3),
                                "house": house_of(r[0], cusps) if cusps else None, "retro": r[3] < 0}
    if time_known:
        lons["ASC"], lons["MC"] = ascmc[0], ascmc[1]
    out["aspects"] = aspects(lons, settings)
    out["input"] = {"local": t.local, "tz": t.tz, "utc_offset": t.utc_offset, "utc": t.utc,
                    "time_status": t.status, "time_known": time_known, "lat": lat, "lon": lon, "place": place,
                    "house_system": settings["house_system"], "zodiac": "tropical",
                    "engine": f"anna-chart-calc {__version__}, Swiss Ephemeris {swe.version}"}
    return out
