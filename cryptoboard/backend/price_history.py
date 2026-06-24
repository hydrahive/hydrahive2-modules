"""Historische Kurse von CoinGecko holen + in den Cache schreiben.

Nutzt client.market_chart(coin_id, "eur", "max") — liefert die gesamte
Kurshistorie in Tagesauflösung als [[ts_ms, price], …]. Pro Coin EIN Call;
danach dauerhaft im price_history_store gecacht (Kurse ändern sich nie).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import client, price_history_store as store

logger = logging.getLogger(__name__)

_VS = "eur"


def _ts_to_day(ts_ms: float) -> str:
    """CoinGecko-Millisekunden-Timestamp → ISO-Tag (UTC)."""
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")


def _to_daily(raw: list) -> dict[str, float]:
    """[[ts_ms, price], …] → {day: price}. Bei mehreren Punkten pro Tag
    gewinnt der letzte (Tages-Schlusskurs)."""
    out: dict[str, float] = {}
    for point in raw:
        if not isinstance(point, list) or len(point) < 2:
            continue
        try:
            day = _ts_to_day(float(point[0]))
            out[day] = float(point[1])
        except (TypeError, ValueError):
            continue
    return out


async def fetch_coin(coin_id: str) -> int:
    """Holt die volle Historie eines Coins und schreibt sie in den Cache.
    Gibt die Anzahl gecachter Tage zurück. Fehler werden geloggt, nicht geworfen."""
    try:
        raw = await client.market_chart(coin_id, _VS, "max")
    except Exception as exc:
        logger.warning("price_history: Abruf für %s fehlgeschlagen: %s", coin_id, exc)
        return 0
    daily = _to_daily(raw)
    if not daily:
        return 0
    return store.upsert_series(coin_id, daily)


async def ensure_coins(coin_ids: list[str], *, force: bool = False) -> dict[str, int]:
    """Stellt sicher, dass für die gegebenen Coins Kurse im Cache sind.

    Ohne force werden nur Coins geladen, die noch GAR NICHT gecacht sind
    (historische Kurse sind unveränderlich; nur der jüngste Tag altert, das
    deckt der reguläre Live-Preis im Portfolio ab). Liefert {coin_id: tage}.
    """
    have = set() if force else store.have_coins()
    out: dict[str, int] = {}
    for cid in coin_ids:
        if cid in have:
            continue
        out[cid] = await fetch_coin(cid)
    return out
