"""Zuletzt gemeldeter Fensterstand je Nutzer (nur im Speicher, letzter Bericht gewinnt)."""
from __future__ import annotations

from datetime import datetime, timezone

from .events import APPS, MAX_WINDOW, EventError

_state: dict[str, dict] = {}


def report(user: str, windows: object) -> dict:
    """Prüft und speichert den Bericht der Brille. Wirft EventError bei ungültigen Daten."""
    if not isinstance(windows, list) or len(windows) > MAX_WINDOW:
        raise EventError(f"windows muss eine Liste mit höchstens {MAX_WINDOW} Einträgen sein")
    clean, seen = [], set()
    for w in windows:
        if not isinstance(w, dict):
            raise EventError("Eintrag muss ein Objekt sein")
        n, app = w.get("window"), w.get("app")
        if not isinstance(n, int) or not 1 <= n <= MAX_WINDOW or n in seen:
            raise EventError("window ungültig oder doppelt")
        if app is not None and app not in APPS:
            raise EventError(f"unbekannte App: {app}")
        seen.add(n)
        clean.append({"window": n, "app": app})
    entry = {"windows": sorted(clean, key=lambda x: x["window"]),
             "reported_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _state[user] = entry
    return entry


def get(user: str) -> dict | None:
    return _state.get(user)


def clear() -> None:
    _state.clear()
