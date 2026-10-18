"""Untertitel des Studios (Spec „Bauplan Etappe 6“): studio/subtitles/<sprache>.json, eine Datei je Sprache.

Immer als eigene Daten, nie ins Bild eingebrannt (Till, 18.10.). Gespeichert wird die ganze Liste mit `revision` gegen
gleichzeitige Änderungen. Jede Prüfregel lehnt die ganze Liste ab.
"""
from __future__ import annotations

import math
import re
from itertools import pairwise
from typing import Any

from . import _clean, plan
from ._store import is_id, new_id, read_json, root, write_json

MAX_CUES = 5000
MAX_TEXT = 200
MIN_SECONDS = 0.5
MAX_SECONDS = 4 * 3600                     # wie die Schnittfassung
EPS = 1e-6
SOURCES = ("manual", "speech", "audio", "translation")


class Invalid(plan.PlanError):
    def __init__(self) -> None:
        super().__init__("studio_subtitles_invalid")


def language(lang: Any) -> str:
    if lang not in _clean.LANGUAGES:
        raise plan.PlanError("studio_not_found", 404)
    return lang


def _path(pid: str, lang: str):
    return root(pid) / "subtitles" / f"{lang}.json"


def clean_text(v: Any) -> str:
    """Höchstens zwei Zeilen, keine Leerzeilen (trennen in SRT Einträge) und kein „-->“ (Zeitzeile)."""
    if not isinstance(v, str):
        return ""
    lines = [re.sub(r"\s+", " ", x).strip() for x in v.replace("\r", "\n").split("\n")]
    return "\n".join(x for x in lines if x).replace("-->", "->")


def _num(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= MAX_SECONDS:
        raise Invalid()
    return float(v)


def _cue(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise Invalid()
    start, end = _num(raw.get("start")), _num(raw.get("end"))
    text = clean_text(raw.get("text"))
    if end - start < MIN_SECONDS - EPS or not text or len(text) > MAX_TEXT:
        raise Invalid()
    return {"id": raw["id"] if is_id(raw.get("id")) else new_id(), "start": round(start, 3), "end": round(end, 3), "text": text}


def clean_cues(raw: Any) -> list[dict]:
    if not isinstance(raw, list) or len(raw) > MAX_CUES:
        raise Invalid()
    cues = sorted((_cue(c) for c in raw), key=lambda c: c["start"])
    for a, b in pairwise(cues):
        if b["start"] < a["end"] - EPS:
            raise Invalid()
    seen: set[str] = set()
    for c in cues:                         # doppelte IDs (z. B. kopiert) bekommen eine neue
        if c["id"] in seen:
            c["id"] = new_id()
        seen.add(c["id"])
    return cues


def load(pid: str, lang: str) -> dict:
    raw = read_json(_path(pid, language(lang)), None)
    if not isinstance(raw, dict):
        return {"language": lang, "source": "", "revision": 0, "cues": []}
    try:
        cues = clean_cues(raw.get("cues"))
    except plan.PlanError:
        cues = []
    rev = raw.get("revision")
    return {"language": lang, "source": raw.get("source") if raw.get("source") in SOURCES else "manual",
            "revision": rev if isinstance(rev, int) and not isinstance(rev, bool) and rev >= 0 else 0, "cues": cues}


def write(pid: str, lang: str, cues: list[dict], revision: Any, source: str) -> dict:
    current = load(pid, lang)["revision"]
    if revision != current or isinstance(revision, bool):
        raise plan.PlanError("studio_subtitles_conflict", 409)
    out = {"language": lang, "source": source, "revision": current + 1, "cues": cues}
    write_json(root(pid, create=True) / "subtitles" / f"{lang}.json", out)
    return out


def save(pid: str, lang: str, data: Any) -> dict:
    language(lang)
    data = data if isinstance(data, dict) else {}
    return write(pid, lang, clean_cues(data.get("cues")), data.get("revision"), "manual")
