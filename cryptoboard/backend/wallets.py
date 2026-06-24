"""Wallet-Aggregation — Adressen × On-Chain-Bestände × Kurs → EUR.

Liefert ZWEI Sichten (Option B):
  - tokens: über ALLE Adressen aggregiert (Symbol → Gesamtmenge, Wert, auf
    welchen Wallets), nach Wert sortiert; bekannter Wert zuerst, dann
    verifizierte ohne Preis, dann der Rest. Nichts wird ausgeblendet.
  - addresses: pro Adresse die Roh-Assets (für die Detail-Aufklappung).

Wert je Asset:
  1. coin_id bekannt  → CoinGecko-Kurs (client.markets)
  2. sonst price_trx  → Tronscan-Preis × TRX-EUR-Kurs
  3. sonst             → Wert unbekannt (value=None), wird trotzdem gezeigt
Getrennt vom Portfolio.
"""
from __future__ import annotations

from . import addresses_store as store, chain_clients, client

_VS = "eur"
_EPS = 1e-12


async def _coin_prices(coin_ids: list[str]) -> dict[str, float]:
    ids = sorted({c for c in coin_ids if c})
    if not ids:
        return {}
    try:
        rows = await client.markets(_VS, ids=ids)
    except Exception:
        return {}
    return {r["id"]: (r.get("price") or 0.0) for r in rows if r.get("id")}


def _asset_value(asset: dict, prices: dict[str, float], trx_eur: float) -> float | None:
    """EUR-Wert eines Assets — oder None wenn unbestimmbar."""
    coin_id = asset.get("coin_id")
    if coin_id and coin_id in prices:
        return asset["amount"] * prices[coin_id]
    ptrx = asset.get("price_trx")
    if ptrx is not None and trx_eur > 0:
        return asset["amount"] * ptrx * trx_eur
    return None


async def balances(user: str) -> dict:
    """Token-aggregierte + adressweise Wallet-Übersicht."""
    addrs = store.list_for(user)

    per_addr: list[dict] = []
    coin_ids: list[str] = []
    for a in addrs:
        assets = await chain_clients.fetch_balance(a["chain"], a["address"])
        coin_ids.extend(x.get("coin_id") for x in assets if x.get("coin_id"))
        per_addr.append({**a, "assets": assets})

    prices = await _coin_prices(coin_ids + ["tron"])
    trx_eur = prices.get("tron", 0.0)

    # --- Token-Aggregation über alle Adressen ---
    agg: dict[str, dict] = {}
    addr_out: list[dict] = []
    for a in per_addr:
        enriched = []
        for x in a["assets"]:
            value = _asset_value(x, prices, trx_eur)
            enriched.append({**x, "value": value})
            key = (x["symbol"], x.get("token_id") or x.get("coin_id") or x["symbol"])
            slot = agg.setdefault(key, {
                "symbol": x["symbol"], "amount": 0.0, "value": 0.0,
                "value_known": False, "verified": bool(x.get("verified")),
                "chain": a["chain"], "wallets": [],
            })
            slot["amount"] += x["amount"]
            if value is not None:
                slot["value"] += value
                slot["value_known"] = True
            slot["verified"] = slot["verified"] or bool(x.get("verified"))
            slot["wallets"].append({
                "label": a["label"] or a["address"][:10], "chain": a["chain"],
                "amount": x["amount"], "value": value,
            })
        addr_out.append({
            "id": a["id"], "chain": a["chain"], "address": a["address"],
            "label": a["label"], "assets": enriched,
        })

    tokens = list(agg.values())
    # Sortierung: bekannter Wert zuerst (absteigend), dann verifiziert, dann Rest
    tokens.sort(key=lambda t: (
        0 if t["value_known"] else 1,
        -t["value"] if t["value_known"] else 0,
        0 if t["verified"] else 1,
        -t["amount"],
    ))
    total = sum(t["value"] for t in tokens if t["value_known"])

    return {
        "currency": _VS.upper(),
        "total": total,
        "tokens": tokens,
        "addresses": addr_out,
    }
