"""Was das Display zeigt: Feiertagsvideo oder Dashboard (Statuszentrale). Reine Logik ohne Geräte.

Regeln (SPEC-STATUSZENTRALE.md, Till 18.10.2026):
- Eingabe an .2 (Leerlauf < 1 s) weckt das Dashboard, auch nachts – aber nur, wenn es verfügbar ist.
- Zurück zum Video nach `return_after` Sekunden ohne Eingabe oder auf Wunsch („Zurück“-Knopf, Datei mode.json).
- Nach „Zurück“ weckt erst eine **neue** Eingabe wieder (sonst würde der Klick auf den Knopf sofort zurückholen).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

WAKE_MS = 1000
BACK_GRACE = 0.5        # Eingaben bis 0,5 s nach „Zurück“ zählen noch zum Klick selbst (Leerlauf ist auf ms gerundet)
RETURN_DEFAULT, RETURN_RANGE = 120, (30, 1800)
_FILE = "mode.json"


def return_seconds(config: dict) -> int:
    v = config.get("dashboard_return_seconds")
    lo, hi = RETURN_RANGE
    return v if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi else RETURN_DEFAULT


class Mode:
    def __init__(self, *, return_after: float = RETURN_DEFAULT):
        self.return_after = return_after
        self.current = "video"
        self._blocked_since: float | None = None      # Zeitpunkt von „Zurück“: ältere Eingaben wecken nicht

    def update(self, *, idle_ms: int | None, available: bool, now: float, back_requested: bool = False) -> str:
        if not available or idle_ms is None:
            self.current = "video"
            return self.current
        last_input = now - idle_ms / 1000
        if back_requested and self.current == "dashboard":
            self.current, self._blocked_since = "video", now
            return self.current
        if self.current == "dashboard":
            if idle_ms >= self.return_after * 1000:
                self.current = "video"
            return self.current
        fresh = idle_ms < WAKE_MS and (self._blocked_since is None or last_input > self._blocked_since + BACK_GRACE)
        if fresh:
            self.current, self._blocked_since = "dashboard", None
        return self.current


def request_back(data_dir: Path) -> None:
    """Vom Backend: „Zurück zum Video“. Der Dienst holt den Wunsch beim nächsten Durchlauf ab."""
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp = data_dir / (_FILE + ".tmp")
    tmp.write_text(json.dumps({"back": True}))
    os.replace(tmp, data_dir / _FILE)


def take_back_request(data_dir: Path) -> bool:
    p = data_dir / _FILE
    try:
        raw = json.loads(p.read_text())
    except (OSError, ValueError):
        p.unlink(missing_ok=True) if p.exists() else None
        return False
    p.unlink(missing_ok=True)
    return isinstance(raw, dict) and raw.get("back") is True
