"""Suchtext → Wörter, Phrasen, Filter (Spec §6). Reine Logik, nie Ausnahmen; Unbekanntes wird zu Text.

Filter: von: an: betreff: hat:anhang vor:JJJJ-MM-TT nach:JJJJ-MM-TT konto: ordner:
Operatoren der FTS-Sprache (OR, NEAR, *, -, ^, Spalten) gibt es nicht – alles ist Text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

MAX_TERMS = 20
TERM_MAX = 100
_TOKEN = re.compile(r'(\w+):(?:"([^"]*)"|(\S*))|"([^"]*)"|(\S+)')
_WORD = re.compile(r"\w+", re.UNICODE)
FIELDS = {"von": "from", "an": "to", "betreff": "subject", "konto": "account", "ordner": "folder",
          "from": "from", "to": "to", "subject": "subject"}


@dataclass
class Query:
    words: list[str] = field(default_factory=list)       # alle müssen vorkommen (Wortanfang)
    phrases: list[list[str]] = field(default_factory=list)
    filters: dict[str, list[str]] = field(default_factory=dict)
    attachment: bool = False
    before: str = ""                                      # ISO-Datum (exklusiv)
    after: str = ""

    @property
    def has_text(self) -> bool:
        return bool(self.words or self.phrases)


def _date(v: str) -> str:
    try:
        return date.fromisoformat(v).isoformat()
    except (TypeError, ValueError):
        return ""


def words_of(text: str) -> list[str]:
    return [w.casefold()[:TERM_MAX] for w in _WORD.findall(text or "")]


def parse(text: str) -> Query:
    q = Query()
    text = (text or "")[:2000].replace("\x00", " ")
    for m in _TOKEN.finditer(text):
        key, qval, val, phrase, word = m.groups()
        if key is not None:
            k, v = key.casefold(), (qval if qval is not None else val) or ""
            if k == "hat" and v.casefold() in ("anhang", "attachment"):
                q.attachment = True
            elif k == "vor" and _date(v):
                q.before = _date(v)
            elif k == "nach" and _date(v):
                q.after = _date(v)
            elif k in FIELDS and v.strip():
                q.filters.setdefault(FIELDS[k], []).append(v.strip().casefold()[:TERM_MAX])
            else:
                q.words += words_of(f"{key} {v}")
        elif phrase is not None:
            ws = words_of(phrase)
            if len(ws) > 1:
                q.phrases.append(ws)
            else:
                q.words += ws
        else:
            q.words += words_of(word)
    q.words = q.words[:MAX_TERMS]
    q.phrases = q.phrases[:5]
    return q


def fts_expr(q: Query) -> str:
    """FTS5-Ausdruck nur aus Wort-Zeichen in Anführungszeichen → nie ein Operator, nie ein Syntaxfehler."""
    parts = [f'"{w}"*' for w in q.words]
    parts += ['"' + " ".join(ph) + '"' for ph in q.phrases]
    return " AND ".join(parts)
