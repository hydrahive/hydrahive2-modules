"""Favoriten-Store — gepinnte Entities pro User, ownership-strikt.

Jede Zeile gehört dem anlegenden User; Lese-/Schreib-/Lösch-Ops filtern immer
auf "user". Fremde Einträge sind unsichtbar und unveränderbar. Hartes Limit
gegen Missbrauch. Keine Secrets — nur entity_id-Referenzen.
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
_MAX = 100
_COLS = "id, entity_id, sort, created_at"


def list_for(user: str) -> list[dict]:
    with db() as c:
        return [
            dict(r)
            for r in c.execute(
                f'SELECT {_COLS} FROM module_homeassistant_favorites '
                'WHERE "user" = ? ORDER BY sort ASC, id ASC',
                (user,),
            ).fetchall()
        ]


def add(user: str, entity_id: str) -> dict:
    with db() as c:
        count = c.execute(
            'SELECT COUNT(*) FROM module_homeassistant_favorites WHERE "user" = ?',
            (user,),
        ).fetchone()[0]
        if count >= _MAX:
            raise ValueError("favorites_full")
        existing = c.execute(
            'SELECT id FROM module_homeassistant_favorites '
            'WHERE "user" = ? AND entity_id = ?',
            (user, entity_id),
        ).fetchone()
        if existing:
            return {"id": existing["id"], "entity_id": entity_id}
        cur = c.execute(
            'INSERT INTO module_homeassistant_favorites ("user", entity_id, sort, created_at) '
            f"VALUES (?, ?, ?, {_NOW})",
            (user, entity_id, count),
        )
        return {"id": cur.lastrowid, "entity_id": entity_id}


def remove(user: str, entity_id: str) -> bool:
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_homeassistant_favorites '
            'WHERE "user" = ? AND entity_id = ?',
            (user, entity_id),
        )
        return cur.rowcount > 0
