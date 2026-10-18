"""Entwurf eines Drehbuchs (Spec „Bauplan B2“): gemeinsames Format für „Aus einer Idee“ und „Aus dem Storyteller“.

Ein Entwurf wird nie gespeichert, sondern nur gezeigt. Erst „Übernehmen“ schickt ihn zurück; dann prüft `clean` ihn
noch einmal vollständig. `strict=False` (Antwort der KI) lässt Unbrauchbares weg, `strict=True` (vom Browser) lehnt
falsche Formen ab. Längen werden in beiden Fällen gekürzt.
"""
from __future__ import annotations

from typing import Any

from . import presets
from ._clean import ELEMENT_KINDS, num, text

MAX_SCENES = 200
MAX_ELEMENTS = 200
MAX_SHOTS = 5
HEAD_KEYS = {"title": 200, "logline": 500, "description": 4000, "style": 2000}


class DraftInvalid(ValueError):
    """Entwurf hat eine falsche Form (nur bei strict)."""


def _key(v: Any) -> str:
    return text(v, 64)


def _keys(v: Any, known: set[str]) -> list[str]:
    out: list[str] = []
    for k in v if isinstance(v, list) else []:
        k = _key(k)
        if k in known and k not in out:
            out.append(k)
    return out[:32]


def _element(v: Any, strict: bool) -> dict | None:
    ok = isinstance(v, dict) and v.get("kind") in ELEMENT_KINDS and _key(v.get("key")) and text(v.get("name"), 200)
    if not ok:
        if strict:
            raise DraftInvalid("element")
        return None
    return {"key": _key(v["key"]), "kind": v["kind"], "name": text(v["name"], 200), "description": text(v.get("description"), 4000)}


def _shot(v: Any, known: set[str], durations: tuple[int, int]) -> dict:
    v = v if isinstance(v, dict) else {}
    key = v.get("shot") if isinstance(v.get("shot"), str) and presets.phrase_for("shot", v["shot"]) else ""
    return {"shot": key, "prompt": text(v.get("prompt"), 2000), "element_keys": _keys(v.get("element_keys"), known),
            "duration": num(v.get("duration"), durations[0], durations[1], 5)}


def _scene(v: Any, known: set[str], strict: bool, durations: tuple[int, int]) -> dict | None:
    if not isinstance(v, dict):
        if strict:
            raise DraftInvalid("scene")
        return None
    shots = v.get("shots") if isinstance(v.get("shots"), list) else []
    return {
        "title": text(v.get("title"), 200), "description": text(v.get("description"), 4000),
        "location": text(v.get("location"), 200), "time_of_day": text(v.get("time_of_day"), 50),
        "element_keys": _keys(v.get("element_keys"), known),
        "shots": [_shot(s, known, durations) for s in shots if isinstance(s, dict)][:MAX_SHOTS],
    }


def clean(data: Any, *, strict: bool, max_scenes: int = MAX_SCENES, durations: tuple[int, int] = (1, 60)) -> dict:
    """Bereinigter Entwurf. Ohne mindestens eine Szene → DraftInvalid (auch bei strict=False)."""
    if not isinstance(data, dict):
        raise DraftInvalid("draft")
    raw_el, raw_sc = data.get("elements", []), data.get("scenes")
    if not isinstance(raw_el, list) or not isinstance(raw_sc, list) or not raw_sc:
        raise DraftInvalid("form")
    if strict and (len(raw_sc) > max_scenes or len(raw_el) > MAX_ELEMENTS):
        raise DraftInvalid("too_many")
    elements: list[dict] = []
    for e in raw_el[:MAX_ELEMENTS]:
        el = _element(e, strict)
        if el and el["key"] not in {x["key"] for x in elements}:
            elements.append(el)
    known = {e["key"] for e in elements}
    scenes = [s for s in (_scene(s, known, strict, durations) for s in raw_sc[:max_scenes]) if s]
    if not scenes:
        raise DraftInvalid("no_scenes")
    head = data.get("head") if isinstance(data.get("head"), dict) else {}
    return {"head": {k: text(head.get(k), n) for k, n in HEAD_KEYS.items()}, "elements": elements, "scenes": scenes}
