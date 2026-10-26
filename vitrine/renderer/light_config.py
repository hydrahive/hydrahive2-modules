"""S8 Licht: Einstellungen der Mainboard-Beleuchtung (SPEC-LICHT.md).

Eine Prüfung für alle wie dash_layout: `normalize()` für den Dienst (Kaputtes → Vorgabe, er läuft immer weiter),
`light_ok()` für das PUT-Schema (lehnt ab), im Cockpit gleich nachgebaut (frontend/light.ts).
"""
from __future__ import annotations

import copy
import re

STATES = ("error", "warning", "done", "working")
EFFECTS = ("static", "breathing", "flashing", "off")
SEASONS = ("spring", "summer", "autumn", "winter")
PCT, BLINK, DONE_SECONDS = (0, 100), (0, 600), (2, 60)
_HEX = re.compile(r"^#?([0-9A-Fa-f]{6})$")

DEFAULTS: dict = {
    "enabled": True,                 # Vitrine steuert das Licht (aus = Licht wird nicht angefasst)
    "brightness": 80,                # Till 26.10.: „kann höher sein“
    "night_off": True,               # folgt dem Zeitfenster des Nachtmodus
    "error_blink_seconds": 20,       # Fehler blinkt so lange ab der Meldung, danach stehend
    "states": {
        "error":   {"effect": "flashing",  "color": "FF0000", "speed": 70, "brightness": None},
        "warning": {"effect": "static",    "color": "FFB000", "speed": 50, "brightness": None},
        "done":    {"effect": "static",    "color": "00FF40", "speed": 50, "brightness": None,
                    "enabled": False, "seconds": 5},
        "working": {"effect": "breathing", "color": "0060FF", "speed": 30, "brightness": None},
    },
    "seasons_enabled": True,
    "seasons": {
        "spring": {"effect": "static", "color": "8CFF66"},
        "summer": {"effect": "static", "color": "FFD7A0"},
        "autumn": {"effect": "static", "color": "FF8C1A"},
        "winter": {"effect": "static", "color": "C8E0FF"},
    },
    "rest_effect": "static",         # Ruhe ohne Jahreszeit-Farben
    "rest_color": "FFD7A0",
}


def color(v) -> str | None:
    """'#ff8800' / 'ff8800' → 'FF8800'; alles andere → None."""
    m = _HEX.match(v) if isinstance(v, str) else None
    return m.group(1).upper() if m else None


def _int_in(v, lo: int, hi: int) -> bool:
    return type(v) is int and lo <= v <= hi                 # bool ausgeschlossen


def _pct_or_none(v) -> bool:
    return v is None or _int_in(v, *PCT)


def _look_ok(d, keys: set[str]) -> bool:
    return (isinstance(d, dict) and set(d) == keys and d.get("effect") in EFFECTS
            and color(d.get("color")) == d.get("color"))


def _state_ok(name: str, d) -> bool:
    keys = set(DEFAULTS["states"][name])
    if not _look_ok(d, keys) or not _int_in(d["speed"], *PCT) or not _pct_or_none(d["brightness"]):
        return False
    if name == "done":
        return type(d["enabled"]) is bool and _int_in(d["seconds"], *DONE_SECONDS)
    return True


def light_ok(d) -> bool:
    if not isinstance(d, dict) or set(d) != set(DEFAULTS):
        return False
    return (type(d["enabled"]) is bool and type(d["night_off"]) is bool and type(d["seasons_enabled"]) is bool
            and _int_in(d["brightness"], *PCT) and _int_in(d["error_blink_seconds"], *BLINK)
            and isinstance(d["states"], dict) and set(d["states"]) == set(STATES)
            and all(_state_ok(n, d["states"][n]) for n in STATES)
            and isinstance(d["seasons"], dict) and set(d["seasons"]) == set(SEASONS)
            and all(_look_ok(d["seasons"][s], {"effect", "color"}) for s in SEASONS)
            and d["rest_effect"] in EFFECTS and color(d["rest_color"]) == d["rest_color"])


def _merge_look(base: dict, raw) -> dict:
    out = copy.deepcopy(base)
    if not isinstance(raw, dict):
        return out
    if raw.get("effect") in EFFECTS:
        out["effect"] = raw["effect"]
    if color(raw.get("color")):
        out["color"] = color(raw["color"])
    for k in ("speed", "seconds", "brightness", "enabled"):
        if k not in base or k not in raw:
            continue
        v = raw[k]
        ok = {"speed": _int_in(v, *PCT), "seconds": _int_in(v, *DONE_SECONDS),
              "brightness": _pct_or_none(v), "enabled": type(v) is bool}[k]
        out[k] = v if ok else None if k == "brightness" else base[k]
    return out


def normalize(raw) -> dict:
    """Für den Dienst: vollständige, gültige Einstellung; Kaputtes wird durch die Vorgabe ersetzt."""
    out = copy.deepcopy(DEFAULTS)
    if not isinstance(raw, dict):
        return out
    for k in ("enabled", "night_off", "seasons_enabled"):
        if type(raw.get(k)) is bool:
            out[k] = raw[k]
    if _int_in(raw.get("brightness"), *PCT):
        out["brightness"] = raw["brightness"]
    if _int_in(raw.get("error_blink_seconds"), *BLINK):
        out["error_blink_seconds"] = raw["error_blink_seconds"]
    if raw.get("rest_effect") in EFFECTS:
        out["rest_effect"] = raw["rest_effect"]
    if color(raw.get("rest_color")):
        out["rest_color"] = color(raw["rest_color"])
    states, seasons = raw.get("states"), raw.get("seasons")
    for n in STATES:
        out["states"][n] = _merge_look(DEFAULTS["states"][n], states.get(n) if isinstance(states, dict) else None)
    for s in SEASONS:
        out["seasons"][s] = _merge_look(DEFAULTS["seasons"][s], seasons.get(s) if isinstance(seasons, dict) else None)
    return out
