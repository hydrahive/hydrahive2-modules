"""Hydra-Zusatzstatus aus <daten>/hydra.json (schreibt das Modul-Backend alle 30 s): laufende Agenten, Fehler/h."""
from __future__ import annotations

import json
import time
from pathlib import Path

STALE = 120.0       # älter → HydraHive läuft vermutlich gerade nicht; nichts anzeigen statt Altes


def extra(data_dir: Path, *, now: float | None = None) -> tuple[str, bool]:
    """(Zusatztext für die Leiste, Alarm?) – Alarm = Fehler in der letzten Stunde."""
    now = time.time() if now is None else now
    try:
        raw = json.loads((data_dir / "hydra.json").read_text())
        if now - float(raw.get("updated") or 0) > STALE:
            return "", False
        agents, errors = int(raw.get("agents") or 0), int(raw.get("errors_last_hour") or 0)
    except (OSError, ValueError, TypeError):
        return "", False
    parts = []
    if agents:
        parts.append(f"{agents} Agent{'en' if agents != 1 else ''} aktiv")
    if errors:
        parts.append(f"{errors} Fehler/h")
    return "  ·  ".join(parts), errors > 0
