"""Gesetzeskorpus speichern und lesen (Spec §4.1).

- Gleicher XML-Hash → nur ``fetched_at`` aktualisieren.
- Neuer Stand → bisherige gültige Normen bekommen ``valid_to``, neue Fassung ``valid_from``. Alte Texte bleiben,
  damit ein Brief seinen Stand behält (``get_norm(..., as_of=…)``).
"""
from __future__ import annotations

import hashlib

from hydrahive.db.connection import db

from .gii_parse import Law

_NORM_COLS = "id, law_key, abbr, enbez, doknr, title, gliederung, text, position, valid_from, valid_to"


def _sha(xml: bytes) -> str:
    return hashlib.sha256(xml).hexdigest()


def save_law(law: Law, xml: bytes, *, fetched_at: str, pinned: bool) -> dict:
    sha = _sha(xml)
    with db() as c:
        row = c.execute("SELECT sha256 FROM module_legal_laws WHERE key = ?", (law.key,)).fetchone()
        if row and row[0] == sha:
            c.execute("UPDATE module_legal_laws SET fetched_at = ?, pinned = MAX(pinned, ?) WHERE key = ?",
                      (fetched_at, int(pinned), law.key))
            return {"key": law.key, "changed": False, "norms": len(law.norms)}
        c.execute(
            "INSERT INTO module_legal_laws(key, abbr, title, stand, sha256, fetched_at, pinned) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET abbr = excluded.abbr, "
            "title = excluded.title, stand = excluded.stand, sha256 = excluded.sha256, "
            "fetched_at = excluded.fetched_at, pinned = MAX(module_legal_laws.pinned, excluded.pinned)",
            (law.key, law.abbr, law.title, law.stand, sha, fetched_at, int(pinned)))
        c.execute("UPDATE module_legal_norms SET valid_to = ? WHERE law_key = ? AND valid_to IS NULL",
                  (fetched_at, law.key))
        c.executemany(
            "INSERT INTO module_legal_norms(law_key, abbr, enbez, doknr, title, gliederung, text, position, valid_from) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(law.key, n.abbr, n.enbez, n.doknr, n.title, n.gliederung, n.text, n.position, fetched_at)
             for n in law.norms])
    return {"key": law.key, "changed": True, "norms": len(law.norms)}


def _law_dict(row) -> dict:
    key, abbr, title, stand, fetched_at, pinned = row
    return {"key": key, "abbr": abbr, "title": title, "stand": stand, "fetched_at": fetched_at, "pinned": bool(pinned)}


def get_law(key: str) -> dict | None:
    with db() as c:
        row = c.execute("SELECT key, abbr, title, stand, fetched_at, pinned FROM module_legal_laws WHERE key = ?",
                        (key,)).fetchone()
    return _law_dict(row) if row else None


def list_laws() -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT key, abbr, title, stand, fetched_at, pinned FROM module_legal_laws "
                         "ORDER BY abbr COLLATE NOCASE").fetchall()
    return [_law_dict(r) for r in rows]


def known_abbrs() -> set[str]:
    with db() as c:
        return {r[0] for r in c.execute("SELECT abbr FROM module_legal_laws")}


def norm_dict(row) -> dict:
    return dict(zip([k.strip() for k in _NORM_COLS.split(",")], row, strict=True))


def get_norm(abbr: str, enbez: str, *, as_of: str | None = None) -> dict | None:
    """Gültige Fassung oder – mit ``as_of`` (ISO) – die Fassung, die zu diesem Zeitpunkt galt."""
    with db() as c:
        if as_of is None:
            row = c.execute(f"SELECT {_NORM_COLS} FROM module_legal_norms WHERE abbr = ? AND enbez = ? "
                            "AND valid_to IS NULL", (abbr, enbez)).fetchone()
        else:
            row = c.execute(f"SELECT {_NORM_COLS} FROM module_legal_norms WHERE abbr = ? AND enbez = ? "
                            "AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?) "
                            "ORDER BY valid_from DESC LIMIT 1", (abbr, enbez, as_of, as_of)).fetchone()
    return norm_dict(row) if row else None


def count_norms(abbr: str, *, include_old: bool = False) -> int:
    sql = "SELECT count(*) FROM module_legal_norms WHERE abbr = ?" + ("" if include_old else " AND valid_to IS NULL")
    with db() as c:
        return c.execute(sql, (abbr,)).fetchone()[0]
