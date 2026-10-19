"""Wer ist im Bild? (Spec „Bauplan H“, H2): genau die am Bild angehakten Bausteine – Figuren, dann Orte, dann Dinge.

Früher (C2) kamen auch alle Bausteine dazu, deren Name irgendwo im Text stand. In echten Projekten holte das Dutzende
Begriffe („Agent“, „Session“ …) und fremde Figuren ins Bild – das Ergebnis war Würfeln. `named` bleibt als Hilfe, um
beim Anlegen einer Geschichte Häkchen vorzuschlagen (sichtbar, abwählbar).
"""
from __future__ import annotations

import re


def _pattern(name: str) -> re.Pattern | None:
    words = name.split()
    if not words:
        return None
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(w) for w in words) + r"(?!\w)", re.IGNORECASE)


def named(text: str, elements: list[dict]) -> list[str]:
    """IDs der Bausteine, deren Name im Text vorkommt (Reihenfolge der Bausteine)."""
    if not text:
        return []
    out = []
    for e in elements:
        p = _pattern(str(e.get("name") or ""))
        if p and p.search(text):
            out.append(e["id"])
    return out


_ORDER = {"character": 0, "place": 1, "object": 2}


def of_shot(scene: dict, shot: dict, elements: list[dict]) -> list[str]:
    """Angehakte, vorhandene Bausteine des Shots ohne Doppelte; Figuren vor Orten vor Dingen (H2). `scene` bleibt
    im Aufruf, damit die Schnittstelle gleich bleibt."""
    kind = {e["id"]: e.get("kind") for e in elements}
    gone = set(shot.get("excluded_ids") or [])
    ticked = [x for x in dict.fromkeys(shot.get("element_ids") or []) if x in kind and x not in gone]
    return sorted(ticked, key=lambda x: _ORDER.get(kind[x], 3))
