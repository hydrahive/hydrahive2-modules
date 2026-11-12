"""Idee auflösen: volle ID oder eindeutiger Anfang (Kurz-ID).

Wie bei den Tasks gilt: eine leere ID trifft nie etwas. Sonst würde ein
Werkzeug mit leerer ID auf die erstbeste Idee des Nutzers wirken.
"""
from __future__ import annotations

from typing import Any

from . import store

MIN_PREFIX = 4


def resolve(username: str, idea_id: Any) -> tuple[dict | None, str | None]:
    """Gibt (Idee, None) oder (None, Fehlertext) zurück. Nur Ideen des Nutzers."""
    wanted = str(idea_id or "").strip()
    if not wanted:
        return None, "Keine idea_id angegeben."
    idea = store.get(username, wanted)
    if idea is not None:
        return idea, None
    if len(wanted) < MIN_PREFIX:
        return None, f"Die Kurz-ID '{wanted}' ist zu kurz (mindestens {MIN_PREFIX} Zeichen)."
    matches = store.ids_with_prefix(username, wanted)
    if len(matches) == 1:
        return store.get(username, matches[0]["id"]), None
    if len(matches) > 1:
        listed = ", ".join(f"{m['id'][:8]} („{m['title'][:40]}“)" for m in matches)
        return None, f"Mehrdeutig, mehrere Ideen beginnen mit '{wanted}': {listed}. Bitte mehr Zeichen angeben."
    return None, f"Idee '{wanted}' nicht gefunden. idea_list zeigt die vorhandenen Ideen."
