"""Anordnung der Statuszentrale (S4): welche Bereiche in welcher Reihenfolge, plus wenige Einstellungen je Bereich.

Eine Prüfung für alle: `config.load` (Dienst), das PUT-Schema (Server) und – gleich nachgebaut – `rules.ts` (Cockpit).
Alte Einträge aus S2 (nur tasks_user, github_project, github_repos) bleiben gültig und werden um Standards ergänzt.
"""
from __future__ import annotations

import copy
import re

AREAS = ("messages", "home", "hydra", "tasks", "github", "machine", "mining")
MESSAGES_MAX = (1, 5)
MAX_ROOMS, ROOM_LEN = 20, 60
_USER = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_ROOM = re.compile(r"^[^<>&\"\x00-\x1f]{1,%d}$" % ROOM_LEN)

DEFAULTS: dict = {
    "tasks_user": "till", "github_project": "Hydrahive DEV",
    "github_repos": ["hydrahive/hydrahive2.0", "hydrahive/hydrahive2-modules"],
    "order": list(AREAS), "hidden": [], "messages_max": 3, "home_rooms": [], "mining_in_machine": True,
}
S2_KEYS = {"tasks_user", "github_project", "github_repos"}


def _repos_ok(repos) -> bool:
    return isinstance(repos, list) and len(repos) <= 5 and all(
        isinstance(r, str) and _REPO.fullmatch(r) and not any(x in (".", "..") for x in r.split("/")) for r in repos)


def _ids_ok(v, unique: bool = True) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x in AREAS for x in v) and (not unique or len(set(v)) == len(v))


def layout_ok(d) -> bool:
    if not isinstance(d, dict) or not S2_KEYS <= set(d) or not set(d) <= set(DEFAULTS):
        return False
    rooms = d.get("home_rooms", [])
    mm = d.get("messages_max", DEFAULTS["messages_max"])
    return (isinstance(d["tasks_user"], str) and bool(_USER.fullmatch(d["tasks_user"]))
            and isinstance(d["github_project"], str) and 0 < len(d["github_project"].strip()) <= 100
            and _repos_ok(d["github_repos"])
            and _ids_ok(d.get("order", [])) and _ids_ok(d.get("hidden", []))
            and type(mm) is int and MESSAGES_MAX[0] <= mm <= MESSAGES_MAX[1]
            and isinstance(rooms, list) and len(rooms) <= MAX_ROOMS
            and all(isinstance(r, str) and _ROOM.fullmatch(r) for r in rooms)
            and type(d.get("mining_in_machine", True)) is bool)


def normalize(d: dict | None) -> dict:
    """Gültige Einstellung (oder {}) → vollständig: fehlende Felder als Standard, fehlende Bereiche hinten angehängt."""
    out = copy.deepcopy(DEFAULTS)
    if d and layout_ok(d):
        out.update(copy.deepcopy(d))
    out["order"] = list(out["order"]) + [a for a in AREAS if a not in out["order"]]
    return out
