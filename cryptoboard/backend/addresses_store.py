"""Adress-Store — Wallet-Adressen pro User, ownership-strikt.

Jede Zeile gehört dem anlegenden User; alle Ops filtern auf "user". Mehrere
Adressen pro Chain erlaubt. Speichert NUR öffentliche Adressen, nie Keys.
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
_MAX = 100


def list_for(user: str) -> list[dict]:
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT id, chain, address, label, added_at '
                'FROM module_cryptoboard_addresses WHERE "user" = ? '
                "ORDER BY chain ASC, added_at ASC",
                (user,),
            ).fetchall()
        ]


def add(user: str, chain: str, address: str, label: str) -> int:
    with db() as c:
        count = c.execute(
            'SELECT COUNT(*) FROM module_cryptoboard_addresses WHERE "user" = ?',
            (user,),
        ).fetchone()[0]
        if count >= _MAX:
            raise ValueError("addresses_full")
        cur = c.execute(
            'INSERT OR IGNORE INTO module_cryptoboard_addresses '
            '("user", chain, address, label, added_at) '
            f"VALUES (?, ?, ?, ?, {_NOW})",
            (user, chain, address, label),
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        # Bereits vorhanden (UNIQUE) → bestehende id zurückgeben
        row = c.execute(
            'SELECT id FROM module_cryptoboard_addresses '
            'WHERE "user" = ? AND chain = ? AND address = ?',
            (user, chain, address),
        ).fetchone()
        return int(row[0]) if row else 0


def remove(user: str, addr_id: int) -> bool:
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_cryptoboard_addresses WHERE "user" = ? AND id = ?',
            (user, addr_id),
        )
        return cur.rowcount > 0
