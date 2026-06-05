"""Watchlist-Store — Coins pro User, ownership-strikt.

Jede Zeile gehört dem anlegenden User; Lese-/Lösch-Ops filtern immer auf
"user". Fremde Einträge sind unsichtbar. Hartes Limit gegen Missbrauch.
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
_MAX = 200


def list_for(user: str) -> list[dict]:
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT coin_id, symbol, name, added_at '
                'FROM module_cryptoboard_watchlist WHERE "user" = ? '
                'ORDER BY added_at DESC',
                (user,),
            ).fetchall()
        ]


def add(user: str, coin_id: str, symbol: str, name: str) -> None:
    with db() as c:
        count = c.execute(
            'SELECT COUNT(*) FROM module_cryptoboard_watchlist WHERE "user" = ?',
            (user,),
        ).fetchone()[0]
        if count >= _MAX:
            raise ValueError("watchlist_full")
        c.execute(
            'INSERT OR IGNORE INTO module_cryptoboard_watchlist '
            '("user", coin_id, symbol, name, added_at) '
            f"VALUES (?, ?, ?, ?, {_NOW})",
            (user, coin_id, symbol, name),
        )


def remove(user: str, coin_id: str) -> None:
    with db() as c:
        c.execute(
            'DELETE FROM module_cryptoboard_watchlist WHERE "user" = ? AND coin_id = ?',
            (user, coin_id),
        )
