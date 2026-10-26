"""Historical time zone resolution. Cases are synthetic (no real people's birth data)."""
import datetime as dt

import pytest

from anna_chart_calc.timeresolve import TimeResolutionError, resolve

KYIV = (50.4547, 30.5239)
SYZRAN = (53.1559, 48.4746)
ADELAIDE = (-34.9285, 138.6007)
NEW_YORK = (40.7128, -74.0060)
PHOENIX = (33.4484, -112.0740)
INDIANAPOLIS = (39.7684, -86.1581)
HONOLULU = (21.3069, -157.8583)
LOS_ANGELES = (34.0522, -118.2437)


def off(local, where, **kw):
    return resolve(dt.datetime.fromisoformat(local), *where, **kw).utc_offset


@pytest.mark.parametrize(("local", "where", "expected"), [
    ("1985-07-15T12:00", KYIV, "+04:00"),        # Soviet Kyiv on Moscow summer time
    ("1985-01-15T12:00", KYIV, "+03:00"),        # Moscow standard time
    ("1995-07-15T12:00", KYIV, "+03:00"),        # independent Ukraine, EEST
    ("2004-12-08T12:00", KYIV, "+02:00"),
    ("1977-08-15T12:00", SYZRAN, "+04:00"),      # USSR had no summer time in 1977
    ("2020-03-09T12:00", ADELAIDE, "+10:30"),    # half-hour zone, daylight saving
    ("2020-07-09T12:00", ADELAIDE, "+09:30"),
    ("1990-07-04T12:00", NEW_YORK, "-04:00"),
    ("1990-01-04T12:00", NEW_YORK, "-05:00"),
    ("1990-07-04T12:00", PHOENIX, "-07:00"),     # Arizona: no daylight saving
    ("1990-07-04T12:00", INDIANAPOLIS, "-05:00"),  # Indiana: no DST until 2006
    ("2010-07-04T12:00", INDIANAPOLIS, "-04:00"),
    ("1990-07-04T12:00", HONOLULU, "-10:00"),
    ("1944-07-04T12:00", LOS_ANGELES, "-07:00"),  # US War Time
])
def test_historical_offsets(local, where, expected):
    assert off(local, where) == expected


def test_zone_found_from_coordinates():
    assert resolve(dt.datetime(2000, 1, 1, 12), *ADELAIDE).tz == "Australia/Adelaide"


def test_nonexistent_time_raises_by_default():
    with pytest.raises(TimeResolutionError) as e:
        resolve(dt.datetime(2021, 3, 14, 2, 30), *NEW_YORK)
    assert e.value.status == "nonexistent"


def test_nonexistent_time_forward():
    r = resolve(dt.datetime(2021, 3, 14, 2, 30), *NEW_YORK, nonexistent="forward")
    assert r.status == "nonexistent_shifted"
    assert r.utc == "2021-03-14T07:30:00+00:00"   # = 03:30 EDT


def test_ambiguous_time_raises_with_options():
    with pytest.raises(TimeResolutionError) as e:
        resolve(dt.datetime(2021, 11, 7, 1, 30), *NEW_YORK)
    assert e.value.status == "ambiguous"
    assert [o["utc_offset"] for o in e.value.options] == ["-04:00", "-05:00"]


@pytest.mark.parametrize(("choice", "utc"), [("earlier", "2021-11-07T05:30:00+00:00"),
                                             ("later", "2021-11-07T06:30:00+00:00")])
def test_ambiguous_time_choice(choice, utc):
    r = resolve(dt.datetime(2021, 11, 7, 1, 30), *NEW_YORK, ambiguous=choice)
    assert (r.utc, r.status) == (utc, "ambiguous_resolved")


def test_fixed_offset_overrides_database():
    r = resolve(dt.datetime(1985, 7, 15, 12), *KYIV, utc_offset="+03:00")
    assert (r.utc, r.tz, r.status) == ("1985-07-15T09:00:00+00:00", None, "fixed_offset")


def test_explicit_zone():
    assert resolve(dt.datetime(1985, 7, 15, 12), tz="Europe/Kyiv").utc_offset == "+04:00"
