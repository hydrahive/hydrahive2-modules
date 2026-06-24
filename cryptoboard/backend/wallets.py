"""Wallet-Aggregation — Adressen × On-Chain-Bestände × Live-Kurs → EUR.

Holt pro Adresse die Bestände (chain_clients), reichert sie mit dem aktuellen
CoinGecko-Kurs an (client.markets) und liefert je Adresse die Assets samt Wert
plus eine Gesamtsumme. Getrennt vom Portfolio (keine Vermischung).
"""
from __future__ import annotations

from . import addresses_store as store, chain_clients, client

_VS = "eur"
_EPS = 1e-12


async def _prices(coin_ids: list[str]) -> dict[str, float]:
    ids = sorted(set(coin_ids))
    if not ids:
        return {}
    try:
        rows = await client.markets(_VS, ids=ids)
    except Exception:
        return {}
    return {r["id"]: (r.get("price") or 0.0) for r in rows if r.get("id")}


async def balances(user: str) -> dict:
    """Alle Adressen des Users mit aktuellen Beständen + EUR-Werten."""
    addrs = store.list_for(user)

    # Bestände je Adresse holen
    per_addr: list[dict] = []
    coin_ids: list[str] = []
    for a in addrs:
        assets = await chain_clients.fetch_balance(a["chain"], a["address"])
        coin_ids.extend(x["coin_id"] for x in assets)
        per_addr.append({**a, "assets": assets})

    prices = await _prices(coin_ids)

    total = 0.0
    out_addrs: list[dict] = []
    for a in per_addr:
        enriched = []
        for x in a["assets"]:
            price = prices.get(x["coin_id"], 0.0)
            value = x["amount"] * price
            total += value
            enriched.append({**x, "price": price, "value": value})
        out_addrs.append({
            "id": a["id"], "chain": a["chain"], "address": a["address"],
            "label": a["label"], "assets": enriched,
        })

    return {"currency": _VS.upper(), "addresses": out_addrs, "total": total}
