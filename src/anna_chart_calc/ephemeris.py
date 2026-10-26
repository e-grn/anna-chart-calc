"""Swiss Ephemeris data files. Bundled files cover 1800-2399 (sepl_18, semo_18, seas_18 from
https://github.com/aloistr/swisseph, AGPL-3.0). Set SE_EPHE_PATH to use another directory."""
from __future__ import annotations

import functools
import os
from pathlib import Path

import swisseph as swe

BUNDLED = Path(__file__).parent / "ephe"


def ephe_path() -> str:
    return os.environ.get("SE_EPHE_PATH") or str(BUNDLED)


@functools.cache
def init_ephemeris() -> None:
    swe.set_ephe_path(ephe_path())
