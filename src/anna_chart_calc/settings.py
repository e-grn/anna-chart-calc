"""Load calculation settings: bundled settings.json, optionally merged with a user file (top-level keys)."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT = Path(__file__).with_name("settings.json")


def load_settings(path: str | Path | None = None) -> dict:
    s = json.loads(DEFAULT.read_text(encoding="utf-8"))
    if path:
        user = json.loads(Path(path).read_text(encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(s.get(k), dict):
                s[k] = {**s[k], **v}
            else:
                s[k] = v
    s.pop("_comment", None)
    return s
