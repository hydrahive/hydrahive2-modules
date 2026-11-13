"""Aussehen je Fernseher → Theme von cleanyourtv (PLAN-E2.md Baustein B).

Gespeichert wird ein kleines, geprüftes Wörterbuch. Daraus entsteht `config.json` mit Schlüsseln aus themes/README.md
(b953804). Nur bekannte Schlüssel mit geprüften Werten – keine freien Eingaben auf dem Fernseher.
"""
from __future__ import annotations

import json
import re

from hydrahive.db.connection import db

PKG = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
MOODS = ("morning", "evening", "night")
MAX_APPS = 60
MAX_LABEL = 24
MAX_NAME = 40

DEFAULT: dict = {
    "dock": [],               # Reihenfolge der Leiste (Pakete)
    "hidden": [],             # nie als Kachel
    "labels": {},             # Paket → eigener Name
    "columns": 6,             # 1–8
    "rows_below_dock": 1,     # 0–3
    "background_color": "#000000",
    "wallpaper_dim": 20,      # 0–90
    "dock_opacity": 85,       # 30–100
    "rotation_minutes": 0,    # 0–1440, Wechsel innerhalb einer Tageszeit
    "sky_intensity": 0,       # 0–100
    "clock_format": "24",     # 12 | 24 | system
    "show_greeting": True,
    "greeting_name": "",
}


class TvwLookError(RuntimeError):
    def __init__(self, code: str, field: str = ""):
        super().__init__(code)
        self.code = code
        self.field = field


def _int(v, lo: int, hi: int, field: str) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise TvwLookError("tvw_look_invalid", field)
    return v


def _pkgs(v, field: str) -> list[str]:
    if not isinstance(v, list) or len(v) > MAX_APPS or not all(isinstance(p, str) and PKG.match(p) for p in v):
        raise TvwLookError("tvw_look_invalid", field)
    return list(dict.fromkeys(v))


def _text(v, limit: int, field: str) -> str:
    if not isinstance(v, str) or len(v) > limit or any(ord(c) < 32 or ord(c) == 127 for c in v):
        raise TvwLookError("tvw_look_invalid", field)
    return v.strip()


def clean(raw: dict) -> dict:
    """Eingabe prüfen und mit Standardwerten auffüllen. Unbekannte Felder werden verworfen."""
    if not isinstance(raw, dict):
        raise TvwLookError("tvw_look_invalid")
    v = {**DEFAULT, **{k: raw[k] for k in DEFAULT if k in raw}}
    labels = v["labels"]
    if not isinstance(labels, dict) or len(labels) > MAX_APPS:
        raise TvwLookError("tvw_look_invalid", "labels")
    out_labels = {}
    for pkg, name in labels.items():
        if not isinstance(pkg, str) or not PKG.match(pkg):
            raise TvwLookError("tvw_look_invalid", "labels")
        name = _text(name, MAX_LABEL, "labels")
        if name:
            out_labels[pkg] = name
    if not isinstance(v["background_color"], str) or not COLOR.match(v["background_color"]):
        raise TvwLookError("tvw_look_invalid", "background_color")
    if v["clock_format"] not in ("12", "24", "system"):
        raise TvwLookError("tvw_look_invalid", "clock_format")
    if not isinstance(v["show_greeting"], bool):
        raise TvwLookError("tvw_look_invalid", "show_greeting")
    return {
        "dock": _pkgs(v["dock"], "dock"), "hidden": _pkgs(v["hidden"], "hidden"), "labels": out_labels,
        "columns": _int(v["columns"], 1, 8, "columns"),
        "rows_below_dock": _int(v["rows_below_dock"], 0, 3, "rows_below_dock"),
        "background_color": v["background_color"].lower(),
        "wallpaper_dim": _int(v["wallpaper_dim"], 0, 90, "wallpaper_dim"),
        "dock_opacity": _int(v["dock_opacity"], 30, 100, "dock_opacity"),
        "rotation_minutes": _int(v["rotation_minutes"], 0, 1440, "rotation_minutes"),
        "sky_intensity": _int(v["sky_intensity"], 0, 100, "sky_intensity"),
        "clock_format": v["clock_format"], "show_greeting": v["show_greeting"],
        "greeting_name": _text(v["greeting_name"], MAX_NAME, "greeting_name"),
    }


def theme_config(look: dict, wallpapers: dict[str, list[str]]) -> dict:
    """config.json für cleanyourtv. `wallpapers`: Tageszeit → Dateinamen im Ordner wallpapers/ (schon geprüft)."""
    files = [f for m in MOODS for f in wallpapers.get(m, [])]
    cfg = {
        "dock_apps": look["dock"], "fill_dock": not look["dock"], "hidden_apps": look["hidden"],
        "app_labels": [f"{p}={n}" for p, n in sorted(look["labels"].items())],
        "columns": look["columns"], "rows_below_dock": look["rows_below_dock"],
        "background_color": look["background_color"], "dock_opacity": look["dock_opacity"],
        "sky_intensity": look["sky_intensity"], "clock_format": look["clock_format"],
        "show_greeting": look["show_greeting"], "greeting_name": look["greeting_name"],
        "wallpaper": bool(files),
    }
    if files:
        cfg["wallpaper_dim"] = look["wallpaper_dim"]
        cfg["wallpaper_rotation_minutes"] = look["rotation_minutes"]
        cfg["wallpaper_order"] = "sequential"
        if any(wallpapers.get(m) for m in MOODS[1:]) or len(wallpapers) > 1:
            cfg["wallpaper_moods"] = {m: wallpapers.get(m) or files for m in MOODS}
    return cfg


def theme_json(look: dict, wallpapers: dict[str, list[str]]) -> bytes:
    return json.dumps(theme_config(look, wallpapers), ensure_ascii=False, indent=1).encode("utf-8")


def load(device_id: str) -> dict:
    with db() as conn:
        r = conn.execute("SELECT look FROM module_tvwerkstatt_looks WHERE device_id = ?", (device_id,)).fetchone()
    if r is None:
        return dict(DEFAULT)
    try:
        return clean(json.loads(r[0]))
    except (ValueError, TvwLookError):
        return dict(DEFAULT)


def save(device_id: str, look: dict) -> dict:
    v = clean(look)
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_looks (device_id, look) VALUES (?, ?) ON CONFLICT(device_id) "
                     "DO UPDATE SET look = excluded.look, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                     (device_id, json.dumps(v, ensure_ascii=False)))
        conn.commit()
    return v
