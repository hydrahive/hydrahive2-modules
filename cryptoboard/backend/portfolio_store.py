"""Portfolio-Store — Transaktions-Ledger pro User, ownership-strikt.

Jede Zeile gehört dem anlegenden User; Lese-/Schreib-/Lösch-Ops filtern immer
auf "user". Fremde Einträge sind unsichtbar und unveränderbar. Hartes Limit
gegen Missbrauch. Geldwerte in EUR.
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"
_MAX = 5000
KINDS = ("buy", "sell", "transfer_in", "transfer_out")

_COLS = "id, coin_id, symbol, name, kind, quantity, price, fee, executed_at, note, created_at"


def list_for(user: str, coin_id: str | None = None) -> list[dict]:
    """Alle Transaktionen des Users, optional auf einen Coin gefiltert.

    Sortiert nach executed_at, id aufsteigend — exakt die FIFO-Reihenfolge.
    """
    sql = f'SELECT {_COLS} FROM module_cryptoboard_transactions WHERE "user" = ?'
    args: list = [user]
    if coin_id:
        sql += " AND coin_id = ?"
        args.append(coin_id)
    sql += " ORDER BY executed_at ASC, id ASC"
    with db() as c:
        return [dict(r) for r in c.execute(sql, tuple(args)).fetchall()]


def get(user: str, tx_id: int) -> dict | None:
    with db() as c:
        row = c.execute(
            f'SELECT {_COLS} FROM module_cryptoboard_transactions '
            'WHERE "user" = ? AND id = ?',
            (user, tx_id),
        ).fetchone()
        return dict(row) if row else None


def add(
    user: str,
    *,
    coin_id: str,
    symbol: str,
    name: str,
    kind: str,
    quantity: float,
    price: float,
    fee: float,
    executed_at: str,
    note: str,
    import_hash: str | None = None,
) -> int:
    if kind not in KINDS:
        raise ValueError("invalid_kind")
    with db() as c:
        count = c.execute(
            'SELECT COUNT(*) FROM module_cryptoboard_transactions WHERE "user" = ?',
            (user,),
        ).fetchone()[0]
        if count >= _MAX:
            raise ValueError("ledger_full")
        cur = c.execute(
            'INSERT INTO module_cryptoboard_transactions '
            '("user", coin_id, symbol, name, kind, quantity, price, fee, executed_at, note, import_hash, created_at) '
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {_NOW})",
            (user, coin_id, symbol, name, kind, quantity, price, fee, executed_at, note, import_hash),
        )
        return int(cur.lastrowid)


def existing_hashes(user: str, hashes: list[str]) -> set[str]:
    """Welche der gegebenen import_hashes hat der User bereits? (Dedup)."""
    if not hashes:
        return set()
    with db() as c:
        placeholders = ",".join("?" * len(hashes))
        rows = c.execute(
            f'SELECT import_hash FROM module_cryptoboard_transactions '
            f'WHERE "user" = ? AND import_hash IN ({placeholders})',
            (user, *hashes),
        ).fetchall()
        return {r[0] for r in rows if r[0]}


def update(
    user: str,
    tx_id: int,
    *,
    kind: str,
    quantity: float,
    price: float,
    fee: float,
    executed_at: str,
    note: str,
) -> bool:
    if kind not in KINDS:
        raise ValueError("invalid_kind")
    with db() as c:
        cur = c.execute(
            'UPDATE module_cryptoboard_transactions SET '
            "kind = ?, quantity = ?, price = ?, fee = ?, executed_at = ?, note = ? "
            'WHERE "user" = ? AND id = ?',
            (kind, quantity, price, fee, executed_at, note, user, tx_id),
        )
        return cur.rowcount > 0


def remove(user: str, tx_id: int) -> bool:
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_cryptoboard_transactions WHERE "user" = ? AND id = ?',
            (user, tx_id),
        )
        return cur.rowcount > 0


def distinct_coins(user: str) -> list[dict]:
    """Coins, zu denen der User Transaktionen hat (für Bulk-Preisabruf)."""
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT coin_id, MAX(symbol) AS symbol, MAX(name) AS name '
                'FROM module_cryptoboard_transactions WHERE "user" = ? '
                "GROUP BY coin_id",
                (user,),
            ).fetchall()
        ]
