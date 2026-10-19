"""Wer ist im Bild? (Spec „C2 im Detail“): angehakte Bausteine + Bausteine, deren Name im Text vorkommt.

Damit wirkt ein Foto an „Hydra“, sobald „Hydra“ im Shot, im Sprechtext oder in Titel/Beschreibung der Szene steht –
ohne dass man Häkchen an zwei Stellen setzen muss. Verglichen wird das ganze Wort, ohne Groß/Klein; mehrteilige Namen
(„Kapitän Ole“) müssen ganz vorkommen.
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


def of_shot(scene: dict, shot: dict, elements: list[dict]) -> list[str]:
    """Angehakt (Shot) → genannt in der Szene → genannt im Shot; ohne Doppelte, nur vorhandene Bausteine."""
    known = {e["id"] for e in elements}
    ticked = [x for x in shot.get("element_ids") or [] if x in known]
    scene_text = " ".join(str(scene.get(k) or "") for k in ("title", "description"))
    shot_text = " ".join(str(shot.get(k) or "") for k in ("prompt", "speech"))
    return list(dict.fromkeys([*ticked, *named(scene_text, elements), *named(shot_text, elements)]))
