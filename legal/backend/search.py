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
#: bm25-Spaltengewichte (abbr, enbez, title, gliederung, text). L0 auf dem echten Korpus (10.715 Normen, 20 Fragen):
#: Titel 8 / Gliederung 2 / Text 1 → Top 1 15/20; alle 1 → 12/20 (Spec §6a).
BM25_WEIGHTS = (0.0, 0.0, 8.0, 2.0, 1.0)
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


_REF = r"\d+[a-z]?"
_JOIN = r"\s*(?:,|und|bis|oder)\s*"
_DETAIL = r"\s+(?:Absatz|Abs\.|Satz|S\.|Nummer|Nr\.|Buchstabe|Buchst\.)\s*(?:\d+[a-z]?|[a-z]\b)"
#: Nach der Nummer: weitere Aufzählung/Absatz/Satz …, dann „des|der <Großgeschrieben>“ = fremdes Gesetz.
_FOREIGN = re.compile(rf"^(?:{_JOIN}{_REF}|{_DETAIL})*\s+(?:des|der)\s+(?!(?:vorstehenden|nachstehenden|folgenden)\b)[A-ZÄÖÜ]")


def cites_number(text: str, num: str) -> bool:
    """Nennt ``text`` die Nummer ``num`` als Paragraf DIESES Gesetzes? Nicht: andere Nummer („§ 536a“, „§ 5361“),
    fremdes Gesetz („§ 1 … des Kreditwesengesetzes“, „§§ 1, 2 oder 2a des …“), Paragraf in einem Artikel eines
    anderen Gesetzes („Artikel 246a § 1“, „des Artikels 250 §§ 1 bis 3“). Fälle aus dem echten BGB (20.10.2026)."""
    pattern = re.compile(rf"(Artikels?\s+{_REF}\s+)?§§?\s*(?:{_REF}{_JOIN})*{re.escape(num)}(?![\da-z])")
    for m in pattern.finditer(text):
        if m.group(1):
            continue
        if _FOREIGN.match(text[m.end():]):
            continue
        return True
    return False


def _citing(abbr: str, enbez: str, limit: int) -> list[dict]:
    """Normen von ``abbr``, die genau diese Nummer als Paragraf dieses Gesetzes nennen (``cites_number``)."""
    if limit <= 0 or not enbez.startswith("§ "):
        return []
    num = enbez.split(" ", 1)[1]
    sql = (f"SELECT {', '.join('n.' + c.strip() for c in store._NORM_COLS.split(','))} "
           "FROM module_legal_norms_fts f JOIN module_legal_norms n ON n.id = f.rowid "
           "WHERE module_legal_norms_fts MATCH ? AND n.valid_to IS NULL AND n.abbr = ? AND n.enbez != ? "
           "ORDER BY n.position LIMIT 500")
    with db() as c:
        rows = c.execute(sql, (f'text : "{num}"', abbr, enbez)).fetchall()
    out = []
    for row in rows:
        n = store.norm_dict(row)
        if cites_number(n["text"], num):
            out.append(_hit(n, [num], "cites"))
            if len(out) >= limit:
                break
    return out


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
        # Nach einer Normbezeichnung: nur Normen desselben Gesetzes, die genau diese Nummer zitieren.
        # Sonst trifft das Kürzel („bgb“) fast alles (live hydratest 20.10.2026: „Anhang EV“ unter § 536c).
        return hits + _citing(cit.abbr, cit.enbez, limit - len(hits))
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
           + f" ORDER BY bm25(module_legal_norms_fts, {', '.join(map(str, BM25_WEIGHTS))}) LIMIT ?")
    params = (match, law, limit) if law else (match, limit)
    with db() as c:
        rows = c.execute(sql, params).fetchall()
    seen = {(h["abbr"], h["enbez"]) for h in hits}
    for row in rows:
        n = store.norm_dict(row)
        if (n["abbr"], n["enbez"]) not in seen:
            hits.append(_hit(n, terms, "text"))
    return hits[:limit]
