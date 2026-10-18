"""Untertitel aus den Sprechtexten der Shots (Spec „Bauplan Etappe 6“, 6a). Kostet nichts.

Reihenfolge und Zeit kommen aus der Schnittfassung: je Shot sein erster Bildclip auf V1; liegt dort eine an den Shot
gebundene Sprache auf A1, gilt deren Länge, sonst die des Bildclips. Der Text wird an Satzgrenzen geteilt (lange Sätze
an Wortgrenzen), umbrochen auf höchstens 2 Zeilen à 42 Zeichen; die Zeit wird nach Textlänge verteilt.
"""
from __future__ import annotations

import re

from . import plan, subtitles, timeline
from ._store import new_id, project_lock

LINE = 42
MAX_CUE_SECONDS = 7.0
_SENTENCE = re.compile(r"(?<=[.!?…])\s+")


def wrap(text: str) -> list[str]:
    """Wortweise in Zeilen ≤ LINE (ein einzelnes überlanges Wort bleibt ganz)."""
    lines: list[str] = []
    for word in text.split():
        if lines and len(lines[-1]) + 1 + len(word) <= LINE:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def chunks(text: str) -> list[str]:
    """Sätze; ein Satz, der nicht in zwei Zeilen passt, wird in Stücke zu je zwei Zeilen geteilt."""
    out: list[str] = []
    for sentence in _SENTENCE.split(" ".join(text.split())):
        lines = wrap(sentence)
        out += ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    return [c for c in out if c]


def _merge_for_time(parts: list[str], seconds: float) -> list[str]:
    """Bekommt ein Teil (Zeit nach Textlänge) weniger als MIN_SECONDS, wird er mit dem kürzeren Nachbarn zusammengelegt."""
    while len(parts) > 1:
        total = sum(len(p) for p in parts)
        short = min(range(len(parts)), key=lambda k: len(parts[k]))
        if seconds * len(parts[short]) / total >= subtitles.MIN_SECONDS:
            break
        other = short - 1 if short == len(parts) - 1 or (short > 0 and len(parts[short - 1]) < len(parts[short + 1])) else short + 1
        i = min(short, other)
        parts[i:i + 2] = [" ".join((parts[i] + " " + parts[i + 1]).split())]
    return parts


def spread(text: str, start: float, seconds: float) -> list[dict]:
    seconds = min(seconds, MAX_CUE_SECONDS * max(1, len(chunks(text))))
    parts = _merge_for_time(chunks(text), seconds)
    weights = [len(p) for p in parts]
    total = sum(weights) or 1
    out, t = [], start
    for n, (p, w) in enumerate(zip(parts, weights, strict=True)):
        end = start + seconds if n == len(parts) - 1 else t + seconds * w / total
        end = min(end, t + MAX_CUE_SECONDS)
        lines = wrap(p) if len(p) > LINE and "\n" not in p else p.split("\n")
        out.append({"id": new_id(), "start": round(t, 3), "end": round(end, 3), "text": subtitles.clean_text("\n".join(lines))})
        t = end
    return out


def build(pid: str) -> tuple[list[dict], int]:
    """Untertitel und Anzahl der Shots mit Sprechtext, die nicht auf der Zeitleiste liegen."""
    tl = timeline.load(pid)
    speech = {s["id"]: (s.get("speech") or "").strip() for sc in plan.list_scenes(pid) for s in sc.get("shots") or []}
    voice = {c["shot_id"]: c for c in timeline.clips_of(tl, "A1") if c.get("shot_id")}
    cues, used = [], set()
    for pic in sorted(timeline.clips_of(tl), key=lambda c: c["start"]):
        sid = pic.get("shot_id")
        if not sid or sid in used or not speech.get(sid):
            continue
        used.add(sid)
        v = voice.get(sid)
        src = v if v else pic
        cues += spread(speech[sid], src["start"], src["out"] - src["in"])
    skipped = sum(1 for sid, text in speech.items() if text and sid not in used)
    return cues, skipped


def from_speech(pid: str, lang: str, *, replace: bool) -> dict:
    subtitles.language(lang)
    with project_lock(pid):
        current = subtitles.load(pid, lang)
        if current["cues"] and not replace:
            raise plan.PlanError("studio_subtitles_not_empty", 409)
        cues, skipped = build(pid)
        if not cues:
            raise plan.PlanError("studio_subtitles_no_speech")
        out = subtitles.write(pid, lang, subtitles.clean_cues(cues), current["revision"], "speech")
    return {**out, "skipped": skipped}
