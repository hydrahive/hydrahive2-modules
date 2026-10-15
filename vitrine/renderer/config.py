"""<daten>/config.json – vom Backend geschrieben, vom Dienst gelesen. Fehlerhafte Inhalte → Standardwerte
(der Dienst läuft immer weiter; die Prüfung mit Fehlermeldung macht das Backend beim Speichern)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

DEFAULTS: dict = {
    "rules": [],
    "default_videos": [],
    "night": {"enabled": False, "from": "23:00", "to": "07:00", "mode": "dim"},
    "rotate_minutes": 10,
}


def load(data_dir: Path) -> dict:
    out = copy.deepcopy(DEFAULTS)
    try:
        raw = json.loads((data_dir / "config.json").read_text())
    except (OSError, ValueError):
        return out
    if not isinstance(raw, dict):
        return out
    if isinstance(raw.get("rules"), list):
        out["rules"] = [r for r in raw["rules"] if isinstance(r, dict)]
    if isinstance(raw.get("default_videos"), list):
        out["default_videos"] = [str(v) for v in raw["default_videos"]]
    if isinstance(raw.get("night"), dict):
        out["night"].update({k: v for k, v in raw["night"].items() if k in out["night"]})
    if isinstance(raw.get("rotate_minutes"), int) and raw["rotate_minutes"] >= 0:
        out["rotate_minutes"] = raw["rotate_minutes"]
    return out


def save(data_dir: Path, config: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp = data_dir / "config.json.tmp"
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2))
    tmp.replace(data_dir / "config.json")


class Watcher:
    """Liefert die Konfiguration beim ersten Aufruf und danach nur, wenn sich die Datei geändert hat."""

    def __init__(self, data_dir: Path):
        self.path = data_dir / "config.json"
        self.data_dir = data_dir
        self._mtime: float | None = None

    def poll(self) -> dict | None:
        try:
            m = self.path.stat().st_mtime
        except OSError:
            m = 0.0
        if m == self._mtime:
            return None
        self._mtime = m
        return load(self.data_dir)
