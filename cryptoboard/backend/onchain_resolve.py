"""Token -> coin_id (B1) und EUR-Tageskurs (B2) für erkannte On-Chain-Swaps.

B1 — coin_id-Auflösung:
  1. nativer Coin (kein Kontrakt)      -> chain_clients.native_coin_id(chain)
  2. bekannter Kontrakt (_EVM-Liste)   -> chain_clients.known_token(chain, ...)
  3. sonst CoinGecko-Kontraktsuche     -> client.contract(platform, address)
     (ein Netz-Call je NEUEM Kontrakt, Ergebnis im Prozess gecacht — nicht
     je Swap, nicht je Lauf erneut)
  4. nicht auflösbar                   -> coin_id=None, unresolved=True
     (Nutzer ordnet in Teil 2b zu, wie beim CSV-Import)

B2 — EUR-Preis:
  Tageskurs aus price_history_store am UTC-Tag von executed_at (ISO-Zeit aus
  Alchemy blockTimestamp). Bevorzugte Kurs-Seite eines Swaps: Stablecoin >
  ETH/WETH > sonstige — die andere Seite bekommt price = Wert / Menge (Decimal).
  Kein Kurs auf keiner Seite (z. B. älter als die 365-Tage-CoinGecko-Historie)
  -> beide Seiten price=None, flag "preis_fehlt".

  Netz-Abrufe begrenzt: price_history.ensure_coins() lädt pro coin_id EINMAL
  die komplette 365-Tage-Historie (kein Abruf je Tag).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from . import chain_clients, client
from . import price_history, price_history_store as price_store

_PLATFORM_BY_CHAIN = {"base": "base", "ethereum": "ethereum"}

# Stablecoins, die bei der Kurs-Seiten-Wahl Vorrang vor ETH/WETH haben.
_STABLE_COIN_IDS = {"usd-coin", "tether", "dai"}
_ETH_COIN_IDS = {"ethereum", "weth"}

_contract_cache: dict[tuple[str, str], dict | None] = {}


async def resolve_coin_id(chain: str, contract: str | None, symbol: str) -> dict:
    """coin_id eines Assets. Rückgabe {coin_id, name, unresolved}.

    `contract` None = natives Asset der Chain. Kontraktsuche wird im Prozess
    gecacht (ein Netz-Call je neuem (chain, contract)-Paar, nicht je Aufruf).
    """
    if contract is None:
        coin_id = chain_clients.native_coin_id(chain)
        return {"coin_id": coin_id, "name": "", "unresolved": coin_id is None}

    known = chain_clients.known_token(chain, contract)
    if known:
        sym, coin_id, _dec = known
        return {"coin_id": coin_id, "name": sym, "unresolved": False}

    cache_key = (chain, contract.lower())
    if cache_key in _contract_cache:
        hit = _contract_cache[cache_key]
        return {"coin_id": hit["id"], "name": hit["name"], "unresolved": False} if hit \
            else {"coin_id": None, "name": "", "unresolved": True}

    platform = _PLATFORM_BY_CHAIN.get(chain)
    hit = None
    if platform:
        try:
            hit = await client.contract(platform, contract)
        except Exception:
            hit = None
    _contract_cache[cache_key] = hit
    if hit:
        return {"coin_id": hit["id"], "name": hit["name"], "unresolved": False}
    return {"coin_id": None, "name": symbol, "unresolved": True}


def clear_contract_cache() -> None:
    """Für Tests — Prozess-Cache zwischen Läufen zurücksetzen."""
    _contract_cache.clear()


def _day(executed_at: str | None) -> str | None:
    """UTC-Tag (YYYY-MM-DD) aus einem ISO-Zeitstempel (Alchemy blockTimestamp)."""
    if not executed_at:
        return None
    try:
        return datetime.fromisoformat(str(executed_at).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return None


def day_of(executed_at: str | None) -> str | None:
    """Öffentlich: UTC-Tag eines Ausführungszeitpunkts (für Preis- und Gas-Tag)."""
    return _day(executed_at)


def _day_price(coin_id: str | None, day: str | None) -> Decimal | None:
    if not coin_id or not day:
        return None
    series = price_store.get_series(coin_id)
    price = series.get(day)
    return Decimal(str(price)) if price is not None else None


def _preference_rank(coin_id: str | None) -> int:
    if coin_id in _STABLE_COIN_IDS:
        return 0
    if coin_id in _ETH_COIN_IDS:
        return 1
    return 2


async def ensure_prices_cached(coin_ids: list[str]) -> None:
    """B2: EINMAL pro coin_id die 365-Tage-Historie laden (falls noch nicht gecacht)."""
    ids = sorted({c for c in coin_ids if c})
    if ids:
        await price_history.ensure_coins(ids)


def price_pair(sell_coin_id: str | None, sell_qty: Decimal, buy_coin_id: str | None, buy_qty: Decimal,
                day: str | None) -> tuple[Decimal | None, Decimal | None, bool]:
    """B2: (sell_price, buy_price, preis_fehlt) für einen Swap — EUR je Einheit.

    Bevorzugte Seite (Stablecoin > ETH/WETH > sonstige) bestimmt den EUR-Wert
    des gesamten Swaps über ihren Tageskurs; die andere Seite bekommt
    price = Wert / Menge. Hat KEINE Seite einen Kurs, sind beide price=None
    und preis_fehlt=True.
    """
    sell_price = _day_price(sell_coin_id, day)
    buy_price = _day_price(buy_coin_id, day)

    if sell_price is None and buy_price is None:
        return None, None, True

    # Bevorzugte Seite: die mit Kurs UND besserem Rang gewinnt; hat nur eine
    # Seite einen Kurs, ist die Wahl ohnehin erzwungen.
    use_sell = sell_price is not None and (
        buy_price is None or _preference_rank(sell_coin_id) <= _preference_rank(buy_coin_id)
    )
    if use_sell:
        value_eur = sell_qty * sell_price
        derived_buy = (value_eur / buy_qty) if buy_qty != 0 else None
        return sell_price, derived_buy, False
    value_eur = buy_qty * buy_price
    derived_sell = (value_eur / sell_qty) if sell_qty != 0 else None
    return derived_sell, buy_price, False
