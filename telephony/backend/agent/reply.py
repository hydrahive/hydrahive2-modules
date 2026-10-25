"""Antwort des Sprachmodells streng prüfen (PLAN-AGENT-2B): nur JSON {say, notes, end}, nur bekannte Felder.

Gesprochen wird nur ``say`` – bereinigt (kein Markdown, keine Links) und gekürzt. Alles Kaputte ergibt eine
höfliche Rückfrage statt Halluzination oder Stille.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

MAX_SAY = 400
FALLBACK_SAY = "Entschuldigung, das habe ich nicht verstanden. Können Sie das bitte wiederholen?"
_TEXT_FIELDS = {"name": 120, "callback_number": 40, "concern": 600, "summary": 600}
_BOOL_FIELDS = ("callback_wanted", "needs_review")
_URL_RE = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.IGNORECASE)
_MDLINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_CUT_SAY_RE = re.compile(r'^\s*\{\s*"say"\s*:\s*"((?:[^"\\]|\\.)*)', re.DOTALL)   # Antwort ohne Ende
_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")
logger = logging.getLogger(__name__)


@dataclass
class Reply:
    say: str
    notes: dict = field(default_factory=dict)
    end: bool = False
    ok: bool = True


def _speakable(text: str) -> str:
    text = _MDLINK_RE.sub(r"\1", text)
    text = _URL_RE.sub("", text)
    text = re.sub(r"[*_`#>|~]+", "", text)
    text = " ".join(text.split())
    if len(text) > MAX_SAY:
        cut = text[:MAX_SAY]
        text = cut[: cut.rfind(" ")] if " " in cut else cut
    return text.strip()


def _find_json(raw: str) -> dict | None:
    start = raw.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(raw)):
            ch = raw[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(raw[start:i + 1])
                    except json.JSONDecodeError:
                        break
                    return obj if isinstance(obj, dict) else None
        start = raw.find("{", start + 1)
    return None


def _notes(raw) -> dict:
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    for k, limit in _TEXT_FIELDS.items():
        v = raw.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = " ".join(v.split())[:limit]
    for k in _BOOL_FIELDS:
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    q = raw.get("open_questions")
    if isinstance(q, list):
        qs = [" ".join(x.split())[:200] for x in q if isinstance(x, str) and x.strip()][:10]
        if qs:
            out["open_questions"] = qs
    return out


def _cut_say(raw: str) -> str:
    """Abgeschnittene Antwort (Längengrenze erreicht): ``say`` bis zum letzten ganzen Satz, sonst leer.

    Notizen und ``end`` werden aus einer halben Antwort bewusst nicht übernommen.
    """
    m = _CUT_SAY_RE.match(raw)
    if not m:
        return ""
    try:
        text = json.loads('"' + m.group(1).rstrip("\\") + '"')
    except json.JSONDecodeError:
        return ""
    ends = list(_SENTENCE_END_RE.finditer(text))
    return text[: ends[-1].end()] if ends else ""


def parse_reply(raw: str) -> Reply:
    obj = _find_json(raw or "")
    say = obj.get("say") if obj else None
    if obj is None and _speakable(_cut_say(raw or "")):
        logger.warning("telephony: Antwort des Sprachmodells abgeschnitten (%d Zeichen) – letzter ganzer Satz", len(raw))
        return Reply(say=_speakable(_cut_say(raw)))
    if not isinstance(say, str) or not _speakable(say):
        logger.warning("telephony: Antwort des Sprachmodells unbrauchbar (%d Zeichen) – Rückfrage", len(raw or ""))
        return Reply(say=FALLBACK_SAY, ok=False)
    return Reply(say=_speakable(say), notes=_notes(obj.get("notes")), end=obj.get("end") is True)


def merge_notes(old: dict, new: dict) -> dict:
    out = dict(old)
    for k, v in new.items():
        if k == "open_questions":
            out[k] = list(dict.fromkeys([*out.get(k, []), *v]))[:10]
        elif v not in ("", None):
            out[k] = v
    return out
