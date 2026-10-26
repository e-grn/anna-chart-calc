"""Chart and transit calculation. Synthetic inputs only (no real people's birth data)."""
import datetime as dt
import json

import pytest

from anna_chart_calc.cli import compute_chart, compute_transits, main
from anna_chart_calc.natal import fmt
from anna_chart_calc.settings import load_settings

S = load_settings()
GREENWICH_J2000 = {"date": "2000-01-01", "time": "12:00", "lat": 51.4779, "lon": 0.0, "tz": "Europe/London"}


def test_j2000_epoch():
    c = compute_chart(GREENWICH_J2000, S)
    assert c["jd"] == 2451545.0
    assert c["planets"]["Sun"]["lon"] == pytest.approx(280.37, abs=0.02)
    assert c["planets"]["Sun"]["pos"].endswith("Capricorn")


def test_chart_structure():
    c = compute_chart({"date": "1990-07-04", "time": "15:20", "lat": 40.7128, "lon": -74.006}, S)
    assert c["input"]["tz"] == "America/New_York" and c["input"]["utc_offset"] == "-04:00"
    assert len(c["cusps"]) == 12 and c["cusps"][0] == c["asc"] and c["cusps"][9] == c["mc"]
    assert set(c["planets"]) == {n for n, _ in S["planets"]}
    assert all(1 <= p["house"] <= 12 for p in c["planets"].values())
    orbs = [a[3] for a in c["aspects"]]
    assert orbs == sorted(orbs)
    assert all(a[1] in S["natal_aspects"] for a in c["aspects"])


def test_position_format():
    assert fmt(256.6489) == "16°38' Sagittarius"
    assert fmt(0.999) == "0°59' Aries"


def test_time_unknown():
    c = compute_chart({"date": "1990-07-04", "time": None, "lat": 40.7128, "lon": -74.006}, S)
    assert c["asc"] is None and c["cusps"] is None
    assert c["input"]["time_known"] is False and c["input"]["local"] == "1990-07-04T12:00:00"
    assert all(p["house"] is None for p in c["planets"].values())
    assert not any("ASC" in a or "MC" in a for a in c["aspects"])
    t = compute_transits(c, S, "2026-01-01", "2026-12-31")
    assert t["ingress"] == [] and t["periods"]


def test_transits_format():
    c = compute_chart({"date": "1990-07-04", "time": "15:20", "lat": 40.7128, "lon": -74.006}, S)
    t = compute_transits(c, S, "2026-01-01", "2028-12-31")
    assert t["periods"] == sorted(t["periods"])
    for start, end, planet, aspect, point in t["periods"]:
        assert start <= end and planet in {n for n, _ in S["transits"]["planets"]}
        assert aspect in S["transits"]["aspects"] and point != "Lilith"
    assert {i[1] for i in t["ingress"][:5]} == {n for n, _ in S["transits"]["planets"]}
    assert all(dt.date.fromisoformat(i[0]) for i in t["ingress"])


def test_cli_run(tmp_path):
    b = tmp_path / "birth.json"
    b.write_text(json.dumps({"date": "1990-07-04", "time": "15:20", "lat": 40.7128, "lon": -74.006,
                             "place": "New York, USA", "transits": {"start": "2026-01-01", "end": "2026-12-31"}}))
    assert main(["run", str(b), "--out-dir", str(tmp_path / "out")]) == 0
    c = json.loads((tmp_path / "out" / "chart.json").read_text(encoding="utf-8"))
    assert c["input"]["place"] == "New York, USA"
    assert (tmp_path / "out" / "transits.json").exists()


def test_cli_nonexistent_time_exit_code(tmp_path, capsys):
    rc = main(["chart", "--date", "2021-03-14", "--time", "02:30", "--lat", "40.7128", "--lon", "-74.006",
               "--out", str(tmp_path / "c.json")])
    assert rc == 2
    assert json.loads(capsys.readouterr().err)["error"] == "nonexistent"


def test_settings_override(tmp_path):
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"house_system": "W", "transits": {"orb": 2.0}}))
    s = load_settings(f)
    assert s["house_system"] == "W" and s["transits"]["orb"] == 2.0 and s["transits"]["step_days"] == 4
