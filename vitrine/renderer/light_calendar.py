"""S8 Licht aus dem Kalender: Anlass (Regel mit eigener Lichtfarbe) und Jahreszeit (SPEC-LICHT.md).

Anders als beim Video zählt für das Licht jede passende, eingeschaltete Regel mit gültiger Lichtfarbe – auch ohne Video.
Höchste Priorität gewinnt, bei gleicher Priorität die erste in der Liste.
"""
from __future__ import annotations

import datetime as dt

from . import calendar, light_config

Look = tuple[str, str, str]          # (Name, Effekt, Farbe RRGGBB)


def occasion(config: dict, now: dt.datetime) -> Look | None:
    best: dict | None = None
    for r in config.get("rules") or []:
        if not isinstance(r, dict) or not r.get("enabled", True) or not light_config.color(r.get("light_color")):
            continue
        try:
            if not calendar.matches(r, now):
                continue
        except (TypeError, ValueError, KeyError):
            continue
        if best is None or r.get("priority", 0) > best.get("priority", 0):
            best = r
    if best is None:
        return None
    effect = best.get("light_effect") if best.get("light_effect") in light_config.EFFECTS else "static"
    return str(best.get("name") or ""), effect, light_config.color(best["light_color"])


def season(now: dt.datetime) -> str:
    for name, (a, b) in calendar.SEASONS.items():
        if (a <= now.month <= b) if a <= b else (now.month >= a or now.month <= b):
            return name
    return "winter"


def rest(light: dict, now: dt.datetime) -> Look:
    """Ruhe-Zustand: Jahreszeit-Farbe oder (abgeschaltet) feste Ruhe-Farbe."""
    if light.get("seasons_enabled", True):
        s = season(now)
        look = light["seasons"][s]
        return s, look["effect"], look["color"]
    return "rest", light["rest_effect"], light["rest_color"]
