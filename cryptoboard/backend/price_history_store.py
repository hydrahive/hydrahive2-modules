"""Cache-Store für historische Tageskurse (EUR), global.

module_cryptoboard_price_history: (coin_id, day) → price. Historische Kurse
ändern sich nie, daher dauerhaft cachebar — ein CoinGecko-Call pro Coin reicht.
Keine User-Spalte: Kurse sind öffentlich.
"""
from __future__ import annotations

from hydrahive.db.connection import db


def get_series(coin_id: str) -> dict[str, float]:
    """Alle gecachten Tageskurse eines Coins als {day: price}."""
    with db() as c:
        rows = c.execute(
            "SELECT day, price FROM module_cryptoboard_price_history "
            "WHERE coin_id = ? ORDER BY day ASC",
            (coin_id,),
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def have_coins() -> set[str]:
    """Coins, für die bereits Kurse gecacht sind."""
    with db() as c:
        rows = c.execute(
            "SELECT DISTINCT coin_id FROM module_cryptoboard_price_history"
        ).fetchall()
    return {r[0] for r in rows}


def latest_day(coin_id: str) -> str | None:
    """Jüngster gecachter Tag eines Coins (für inkrementelles Nachladen)."""
    with db() as c:
        row = c.execute(
            "SELECT MAX(day) FROM module_cryptoboard_price_history WHERE coin_id = ?",
            (coin_id,),
        ).fetchone()
    return row[0] if row and row[0] else None


def upsert_series(coin_id: str, series: dict[str, float]) -> int:
    """Tageskurse einfügen/aktualisieren. Gibt die Anzahl geschriebener Tage."""
    if not series:
        return 0
    with db() as c:
        c.executemany(
            "INSERT INTO module_cryptoboard_price_history (coin_id, day, price) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(coin_id, day) DO UPDATE SET price = excluded.price",
            [(coin_id, day, price) for day, price in series.items()],
        )
    return len(series)
