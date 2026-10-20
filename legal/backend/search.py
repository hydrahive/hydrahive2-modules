"""Suche im Gesetzeskorpus: erst exakte Normbezeichnung, sonst SQLite-FTS5 (Spec §4.1, L0 §6a).

Die Anfrage wird nie roh an FTS5 gegeben: nur Wörter (\\w+), jedes als Präfix in Anführungszeichen,
mit OR verknüpft – keine FTS-Syntax von außen (Spalten, NEAR, Klammern).
Gewichtung bm25: Überschrift 8, Gliederung 2, Text 1 (gemessen in L0).
"""
from __future__ import annotations

import re

from hydrahive.db.connection import db

from . import corpus_store as store
from .citation import parse_citation

MAX_LIMIT = 20
_STOP = {"der", "die", "das", "und", "oder", "mit", "von", "für", "nach", "gegen", "wegen", "dem", "den", "des",
         "ein", "eine", "einer", "eines", "bei", "zur", "zum", "auf", "aus", "ist", "sind", "im", "in", "an"}
_SNIPPET = 280


class SearchError(ValueError):
    pass


def _terms(query: str) -> list[str]:
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2 and w not in _STOP]
    # Präfix: Wortende kappen (Mangel/Mängel, Mieter/Mietern) – grober Stamm, in L0 gemessen
    return [w[: max(4, len(w) - 2)] for w in dict.fromkeys(words)]


def _snippet(text: str, terms: list[str]) -> str:
    low = text.lower()
    pos = min((low.find(t) for t in terms if low.find(t) >= 0), default=0)
    start = max(0, pos - 60)
    s = text[start:start + _SNIPPET].replace("\n", " ")
    return ("… " if start else "") + s.strip() + (" …" if start + _SNIPPET < len(text) else "")


def _hit(n: dict, terms: list[str], match: str) -> dict:
    return {"abbr": n["abbr"], "enbez": n["enbez"], "title": n["title"],
            "heading": n["title"] or n["gliederung"], "snippet": _snippet(n["text"], terms), "match": match,
            "law_key": n["law_key"]}


def search(query: str, *, law: str | None = None, limit: int = 10) -> list[dict]:
    query = (query or "").strip()
    if not query:
        raise SearchError("Leere Suche")
    limit = max(1, min(MAX_LIMIT, int(limit)))
    hits: list[dict] = []
    cit = parse_citation(query, store.known_abbrs())
    if cit and (not law or law == cit.abbr):
        n = store.get_norm(cit.abbr, cit.enbez)
        if n:
            hits.append(_hit(n, [], "exact"))
    terms = _terms(query)
    if not terms:
        if hits:
            return hits
        raise SearchError("Keine Suchwörter erkannt")
    match = " OR ".join(f'"{t}"*' for t in terms)
    sql = (f"SELECT {', '.join('n.' + c.strip() for c in store._NORM_COLS.split(','))} "
           "FROM module_legal_norms_fts f JOIN module_legal_norms n ON n.id = f.rowid "
           "WHERE module_legal_norms_fts MATCH ? AND n.valid_to IS NULL"
           + (" AND n.abbr = ?" if law else "")
           + " ORDER BY bm25(module_legal_norms_fts, 0.0, 0.0, 8.0, 2.0, 1.0) LIMIT ?")
    params = (match, law, limit) if law else (match, limit)
    with db() as c:
        rows = c.execute(sql, params).fetchall()
    seen = {(h["abbr"], h["enbez"]) for h in hits}
    for row in rows:
        n = store.norm_dict(row)
        if (n["abbr"], n["enbez"]) not in seen:
            hits.append(_hit(n, terms, "text"))
    return hits[:limit]
