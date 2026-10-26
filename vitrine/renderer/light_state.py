"""S8 Licht: welcher Zustand gilt gerade (SPEC-LICHT.md).

Reihenfolge: Nacht > Fehler > Wartet > Fertig > Arbeitet > Anlass > Jahreszeit/Ruhe. Liest nur, was die Vitrine schon hat:
config.json (Licht, Nachtmodus, Kalender), inbox/ (Meldungen) und hydra.json (laufende Agenten).
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import inbox, light_calendar, night

HYDRA_STALE = 120.0                  # wie hydra_state.STALE: älter → HydraHive läuft nicht


@dataclass
class Look:
    state: str                       # night | error | warning | done | working | occasion | spring … | rest
    effect: str                      # static | breathing | flashing | off
    color: str                       # RRGGBB
    brightness: int
    speed: int = 50
    label: str = ""                  # z. B. Name des Anlasses (nur Anzeige)

    def key(self) -> tuple:
        """Ändert sich der Schlüssel, wird das Licht neu gesetzt (die Anzeige-Bezeichnung zählt nicht)."""
        return self.state, self.effect, self.color, self.brightness, self.speed


@dataclass
class Memory:
    """Was sich der Licht-Thread zwischen zwei Durchläufen merkt (für „Fertig“)."""
    agents: int = 0
    done_until: float = 0.0
    extra: dict = field(default_factory=dict)


def _agents(data: Path, now: float) -> int:
    try:
        raw = json.loads((data / "hydra.json").read_text())
        if now - float(raw.get("updated") or 0) > HYDRA_STALE:
            return 0
        return max(0, int(raw.get("agents") or 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def _unread(data: Path, now: float) -> tuple[dict | None, bool]:
    """(neueste ungelesene Fehlermeldung, gibt es eine ungelesene Warnung?)"""
    try:
        new, _read = inbox.recent(data, now=now)
    except (OSError, ValueError):
        return None, False
    errors = [m for m in new if m.get("kind") == "error"]
    return (errors[0] if errors else None), any(m.get("kind") == "warning" for m in new)


def _state_look(light: dict, name: str, **over) -> Look:
    s = light["states"][name]
    b = s["brightness"] if s["brightness"] is not None else light["brightness"]
    return Look(name, over.get("effect", s["effect"]), s["color"], b, s["speed"])


def choose(data: Path, config: dict, now: dt.datetime, mem: Memory) -> Look | None:
    """Zustand für jetzt. None = Licht nicht anfassen (im Cockpit ausgeschaltet)."""
    light = config.get("light") or {}
    if not light.get("enabled"):
        return None
    t = now.timestamp()
    agents = _agents(data, t)
    done_cfg = light["states"]["done"]
    if mem.agents > 0 and agents == 0 and done_cfg["enabled"]:
        mem.done_until = t + done_cfg["seconds"]
    mem.agents = agents

    if light["night_off"] and night.active(config.get("night") or {}, now):
        return Look("night", "off", "000000", 0)
    err, warn = _unread(data, t)
    if err is not None:
        blinking = t - float(err.get("created") or 0) < light["error_blink_seconds"]
        return _state_look(light, "error", **({} if blinking else {"effect": "static"}))
    if warn:
        return _state_look(light, "warning")
    if t < mem.done_until:
        return _state_look(light, "done")
    if agents > 0:
        return _state_look(light, "working")
    occ = light_calendar.occasion(config, now)
    if occ is not None:
        label, effect, color = occ
        return Look("occasion", effect, color, light["brightness"], 50, label=label)
    name, effect, color = light_calendar.rest(light, now)
    return Look(name, effect, color, light["brightness"], 50)
