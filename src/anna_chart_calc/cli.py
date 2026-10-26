"""anna-chart-calc command line.

  anna-chart-calc resolve-time --date 2004-12-08 --time 11:45 --lat 50.62 --lon 26.25
  anna-chart-calc chart    --date 2004-12-08 --time 11:45 --lat 50.62 --lon 26.25 [--tz ZONE | --utc-offset +02:00]
                           [--ambiguous earlier|later] [--nonexistent forward] [--place TEXT] --out chart.json
  anna-chart-calc chart    --date 2004-12-08 --time-unknown --lat ... --lon ... --out chart.json
  anna-chart-calc transits --chart chart.json [--start 2026-01-01 --end 2036-12-31] [--lat --lon] --out transits.json
  anna-chart-calc run      birth.json --out-dir DIR          # chart.json + transits.json from one input file

Exit code 2 with a JSON error on stderr when the local time is ambiguous or did not exist (clock change),
so the caller can ask the customer. Source code: https://github.com/e-grn/anna-chart-calc (AGPL-3.0).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .natal import natal_chart
from .settings import load_settings
from .timeresolve import TimeResolutionError, resolve
from .transits import default_range, transits


def write_chart(chart: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(chart, indent=1, ensure_ascii=False), encoding="utf-8")


def write_transits(tr: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(tr, indent=0), encoding="utf-8")


def _local(date: str, time: str | None, settings: dict) -> tuple[dt.datetime, bool]:
    known = bool(time)
    t = dt.time.fromisoformat(time if known else settings["time_unknown_local_time"])
    return dt.datetime.combine(dt.date.fromisoformat(date), t), known


def compute_chart(b: dict, settings: dict) -> dict:
    local, known = _local(b["date"], b.get("time"), settings)
    t = resolve(local, b["lat"], b["lon"], tz=b.get("tz"), utc_offset=b.get("utc_offset"),
                ambiguous=b.get("ambiguous", "error"), nonexistent=b.get("nonexistent", "error"))
    return natal_chart(t, b["lat"], b["lon"], settings, time_known=known, place=b.get("place"))


def compute_transits(chart: dict, settings: dict, start: str | None = None, end: str | None = None,
                     lat: float | None = None, lon: float | None = None) -> dict:
    s0, e0 = default_range(settings["transits"]["years"])
    inp = chart.get("input") or {}
    return transits(chart, lat if lat is not None else inp.get("lat"), lon if lon is not None else inp.get("lon"),
                    settings, dt.date.fromisoformat(start) if start else s0, dt.date.fromisoformat(end) if end else e0)


def _birth_args(p):
    p.add_argument("--date", required=True, help="YYYY-MM-DD, local")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--time", help="HH:MM[:SS], local clock time")
    g.add_argument("--time-unknown", action="store_true")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True, help="east positive")
    z = p.add_mutually_exclusive_group()
    z.add_argument("--tz", help="IANA zone, e.g. Europe/Kyiv (default: found from coordinates)")
    z.add_argument("--utc-offset", help="fixed offset, e.g. +03:00 (overrides the tz database)")
    p.add_argument("--ambiguous", choices=("error", "earlier", "later"), default="error")
    p.add_argument("--nonexistent", choices=("error", "forward"), default="error")
    p.add_argument("--place")


def _birth(a) -> dict:
    return {"date": a.date, "time": None if a.time_unknown else a.time, "lat": a.lat, "lon": a.lon,
            "tz": a.tz, "utc_offset": a.utc_offset, "ambiguous": a.ambiguous, "nonexistent": a.nonexistent,
            "place": getattr(a, "place", None)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="anna-chart-calc", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", help="JSON file merged over the bundled settings.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("resolve-time")
    _birth_args(p)
    p = sub.add_parser("chart")
    _birth_args(p)
    p.add_argument("--out", required=True)
    p = sub.add_parser("transits")
    p.add_argument("--chart", required=True)
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--out", required=True)
    p = sub.add_parser("run")
    p.add_argument("birth_json")
    p.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    settings = load_settings(a.settings)
    try:
        if a.cmd == "resolve-time":
            b = _birth(a)
            local, _ = _local(b["date"], b["time"], settings)
            print(json.dumps(resolve(local, a.lat, a.lon, a.tz, a.utc_offset, a.ambiguous, a.nonexistent).to_json(),
                             indent=1))
        elif a.cmd == "chart":
            write_chart(compute_chart(_birth(a), settings), a.out)
        elif a.cmd == "transits":
            chart = json.loads(Path(a.chart).read_text(encoding="utf-8"))
            write_transits(compute_transits(chart, settings, a.start, a.end, a.lat, a.lon), a.out)
        elif a.cmd == "run":
            b = json.loads(Path(a.birth_json).read_text(encoding="utf-8"))
            out = Path(a.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            chart = compute_chart(b, settings)
            write_chart(chart, out / "chart.json")
            tr = b.get("transits") or {}
            write_transits(compute_transits(chart, settings, tr.get("start"), tr.get("end")), out / "transits.json")
    except TimeResolutionError as e:
        print(json.dumps({"error": e.status, "message": str(e), "options": e.options}, indent=1), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
