"""Vorschau auf dem Display: 30 s lang das Programm eines anderen Zeitpunkts (z. B. Heiligabend), danach zurück.

Das Backend legt <daten>/preview.json {"at": ISO-Zeitpunkt, "until": Unix-Zeit} ab; der Dienst liest sie bei der
Programmwahl. Uhr, Datum und Status bleiben echt – nur Video, Regel, Feiertag und Nachtmodus kommen vom Zeitpunkt.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import time
from pathlib import Path

from . import program

SECONDS = 30
_FILE = "preview.json"


def start(data: Path, at: dt.datetime, *, t: float | None = None) -> dict:
    t = time.time() if t is None else t
    raw = {"at": at.replace(second=0, microsecond=0).isoformat(), "until": t + SECONDS}
    data.mkdir(parents=True, exist_ok=True)
    tmp = data / (_FILE + ".tmp")
    tmp.write_text(json.dumps(raw))
    tmp.replace(data / _FILE)
    return raw


def stop(data: Path) -> bool:
    p = data / _FILE
    if not p.exists():
        return False
    p.unlink(missing_ok=True)
    return True


def active(data: Path, *, t: float | None = None) -> dt.datetime | None:
    """Zeitpunkt der laufenden Vorschau oder None. Abgelaufene Datei wird aufgeräumt, kaputte ignoriert."""
    t = time.time() if t is None else t
    p = data / _FILE
    try:
        raw = json.loads(p.read_text())
        at = dt.datetime.fromisoformat(raw["at"])
        until = float(raw["until"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if t >= until:
        p.unlink(missing_ok=True)
        return None
    return at


def label(at: dt.datetime) -> str:
    return f"Vorschau {at:%d.%m. %H:%M}"


def headline(p: program.Program) -> str | None:
    """Zeile unter dem Datum: Vorschau-Hinweis und/oder Feiertagsname."""
    parts = [x for x in (p.preview, p.holiday) if x]
    return " · ".join(parts) or None


def current(data: Path, config: dict, now: dt.datetime, *, t: float | None = None) -> program.Program:
    """Programm für jetzt – oder, während einer Vorschau, für deren Zeitpunkt (mit Hinweistext)."""
    at = active(data, t=t)
    if at is None:
        return program.current(data, config, now)
    return dataclasses.replace(program.current(data, config, at), preview=label(at))
