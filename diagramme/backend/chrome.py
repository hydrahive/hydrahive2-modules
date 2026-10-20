"""Chromium für die Browser-Prüfung von Archify finden (Spec §5).

Reihenfolge: Umgebungsvariable HH_DIAGRAMME_CHROME (Admin-Einstellung), sonst die Playwright-Installation des Kerns
im Home des Dienst-Nutzers. Ohne Chromium baut Archify trotzdem, die Browser-Prüfung wird übersprungen.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV = "HH_DIAGRAMME_CHROME"


def _candidates() -> list[Path]:
    base = Path.home() / ".cache" / "ms-playwright"
    return sorted(base.glob("chromium-*/chrome-linux*/chrome"), reverse=True)


def find() -> str | None:
    own = os.environ.get(ENV, "").strip()
    if own:
        return own if Path(own).is_file() and os.access(own, os.X_OK) else None
    for path in _candidates():
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None
