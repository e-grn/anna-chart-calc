"""Local birth time -> UTC, using the historical IANA time zone rules for the birth place and date.

The time zone is found from the coordinates (timezonefinder) unless given explicitly. The offset for the
birth date comes from the IANA tz database (zoneinfo + tzdata), so summer time and historical changes
(e.g. Moscow time in Soviet Ukraine until 1990) are applied as they were at that date.

Clock changes create two special cases:
  * nonexistent - the local time was skipped when clocks went forward (e.g. 02:30 on a spring-forward night);
  * ambiguous   - the local time happened twice when clocks went back.
Both raise TimeResolutionError by default, so the caller (the order form) can ask the customer.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass
from zoneinfo import ZoneInfo

from timezonefinder import TimezoneFinder

UTC = dt.timezone.utc


class TimeResolutionError(ValueError):
    def __init__(self, status: str, message: str, options: list[dict] | None = None):
        super().__init__(message)
        self.status = status
        self.options = options or []


@dataclass
class ResolvedTime:
    local: str          # ISO local date-time as given
    tz: str | None      # IANA zone name, None when a fixed offset was given
    utc_offset: str     # e.g. "+03:00"
    utc: str            # ISO UTC date-time
    status: str         # "ok" | "ambiguous_resolved" | "nonexistent_shifted" | "fixed_offset"
    utc_datetime: dt.datetime

    def to_json(self) -> dict:
        d = asdict(self)
        d.pop("utc_datetime")
        return d


def _fmt_offset(td: dt.timedelta) -> str:
    total = int(td.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{sign}{h:02d}:{m:02d}" + (f":{s:02d}" if s else "")


def parse_offset(s: str) -> dt.timezone:
    m = re.fullmatch(r"([+-])(\d{1,2}):?(\d{2})?", s.strip())
    if not m:
        raise ValueError(f"bad UTC offset: {s!r} (expected e.g. +03:00 or -0530)")
    sign = -1 if m.group(1) == "-" else 1
    return dt.timezone(sign * dt.timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0)))


def timezone_at(lat: float, lon: float) -> str:
    tf = TimezoneFinder()
    name = tf.timezone_at(lng=lon, lat=lat) or tf.timezone_at_land(lng=lon, lat=lat)
    if not name:
        raise TimeResolutionError("no_timezone", f"no time zone found for {lat}, {lon}")
    return name


def resolve(local: dt.datetime, lat: float | None = None, lon: float | None = None, tz: str | None = None,
            utc_offset: str | None = None, ambiguous: str = "error", nonexistent: str = "error") -> ResolvedTime:
    """local: naive local date-time. ambiguous: error|earlier|later. nonexistent: error|forward."""
    if local.tzinfo is not None:
        raise ValueError("local time must be naive")
    if utc_offset:
        aware = local.replace(tzinfo=parse_offset(utc_offset))
        u = aware.astimezone(UTC)
        return ResolvedTime(local.isoformat(), None, _fmt_offset(aware.utcoffset()), u.isoformat(), "fixed_offset", u)
    if tz is None:
        if lat is None or lon is None:
            raise ValueError("give tz, utc_offset, or coordinates")
        tz = timezone_at(lat, lon)
    zi = ZoneInfo(tz)
    a0, a1 = local.replace(tzinfo=zi, fold=0), local.replace(tzinfo=zi, fold=1)
    u0, u1 = a0.astimezone(UTC), a1.astimezone(UTC)
    status = "ok"
    chosen = a0
    if u0 != u1:
        exists = u0.astimezone(zi).replace(tzinfo=None) == local or u1.astimezone(zi).replace(tzinfo=None) == local
        opts = [{"choice": "earlier", "utc_offset": _fmt_offset(a0.utcoffset()), "utc": min(u0, u1).isoformat()},
                {"choice": "later", "utc_offset": _fmt_offset(a1.utcoffset()), "utc": max(u0, u1).isoformat()}]
        if exists:  # clocks went back: the time happened twice
            if ambiguous == "error":
                raise TimeResolutionError("ambiguous", f"{local} happened twice in {tz} (clocks went back)", opts)
            chosen = a0 if ambiguous == "earlier" else a1
            status = "ambiguous_resolved"
        else:       # clocks went forward: the time never existed
            if nonexistent == "error":
                raise TimeResolutionError("nonexistent", f"{local} did not exist in {tz} (clocks went forward)")
            # "forward": read the clock time with the offset that was in force before the jump,
            # i.e. 02:30 on a spring-forward night becomes 03:30 summer time.
            chosen = a0
            status = "nonexistent_shifted"
    u = chosen.astimezone(UTC)
    return ResolvedTime(local.isoformat(), tz, _fmt_offset(chosen.utcoffset()), u.isoformat(), status, u)
