"""<daten>/config.json – vom Backend geschrieben, vom Dienst gelesen. Fehlerhafte Inhalte → Standardwerte
(der Dienst läuft immer weiter; die Prüfung mit Fehlermeldung macht das Backend beim Speichern)."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

DEFAULTS: dict = {
    "rules": [],
    "default_videos": [],
    "night": {"enabled": False, "from": "23:00", "to": "07:00", "mode": "dim"},
    "rotate_minutes": 10,
    "fps": 24,                  # Bildrate (12–30); Atelier-Videos haben 24
    "message_seconds": 15,      # Standard-Dauer einer Einblendung (5–120); Fehler bleiben länger
    "dashboard_return_seconds": 120,   # Dashboard → zurück zum Video nach so vielen Sekunden ohne Eingabe (30–1800)
    "dashboard": {"tasks_user": "till", "github_project": "Hydrahive DEV",          # Statuszentrale S2
                  "github_repos": ["hydrahive/hydrahive2", "hydrahive/hydrahive2-modules"]},
}
_USER = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")


def dashboard_ok(d) -> bool:
    """Gemeinsame Prüfung für load() und das PUT-Schema (eine Wahrheit)."""
    if not isinstance(d, dict) or set(d) != {"tasks_user", "github_project", "github_repos"}:
        return False
    repos = d["github_repos"]
    return (isinstance(d["tasks_user"], str) and bool(_USER.fullmatch(d["tasks_user"]))
            and isinstance(d["github_project"], str) and 0 < len(d["github_project"].strip()) <= 100
            and isinstance(repos, list) and len(repos) <= 5
            and all(isinstance(r, str) and _REPO.fullmatch(r) and not any(x in (".", "..") for x in r.split("/"))
                    for r in repos))
FPS_RANGE, MESSAGE_RANGE, RETURN_RANGE = (12, 30), (5, 120), (30, 1800)


def _int_in(v, lo: int, hi: int) -> bool:
    return isinstance(v, int) and lo <= v <= hi             # bool ist int, liegt aber immer außerhalb (0/1)


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
    if _int_in(raw.get("fps"), *FPS_RANGE):
        out["fps"] = raw["fps"]
    if _int_in(raw.get("message_seconds"), *MESSAGE_RANGE):
        out["message_seconds"] = raw["message_seconds"]
    if _int_in(raw.get("dashboard_return_seconds"), *RETURN_RANGE):
        out["dashboard_return_seconds"] = raw["dashboard_return_seconds"]
    if dashboard_ok(raw.get("dashboard")):
        out["dashboard"] = copy.deepcopy(raw["dashboard"])
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
