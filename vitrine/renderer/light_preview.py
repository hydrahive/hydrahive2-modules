"""S8 Licht-Vorschau: 15 s lang einen Zustand zeigen (Cockpit-Knopf), danach zurück. Wie preview.py fürs Display:
das Backend legt <daten>/light_preview.json {"state": …, "until": Unix-Zeit} ab, der Licht-Thread liest sie."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import light_config

SECONDS = 15
STATES = (*light_config.STATES, *light_config.SEASONS, "occasion", "rest", "night")
_FILE = "light_preview.json"


def start(data: Path, state: str, *, t: float | None = None) -> dict:
    if state not in STATES:
        raise ValueError(f"state: eine von {', '.join(STATES)}")
    t = time.time() if t is None else t
    raw = {"state": state, "until": t + SECONDS}
    data.mkdir(parents=True, exist_ok=True)
    tmp = data / (_FILE + ".tmp")
    tmp.write_text(json.dumps(raw))
    tmp.replace(data / _FILE)
    return raw


def active(data: Path, *, t: float | None = None) -> str | None:
    t = time.time() if t is None else t
    p = data / _FILE
    try:
        raw = json.loads(p.read_text())
        state, until = raw["state"], float(raw["until"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if t >= until or state not in STATES:
        p.unlink(missing_ok=True)
        return None
    return state
