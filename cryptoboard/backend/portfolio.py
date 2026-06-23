"""Portfolio-Aggregation — Holdings + P&L aus Ledger × Live-Preisen.

Verbindet die reine FIFO-Engine (fifo.py) mit dem Store (portfolio_store.py) und
aktuellen CoinGecko-Kursen (client.py). Liefert pro Coin eine Position und eine
Gesamt-Summary. Alle Geldwerte in EUR.
"""
from __future__ import annotations

from itertools import groupby

from . import client, fifo, portfolio_store as store

_VS = "eur"
_EPS = 1e-9


def _positions_from_ledger(user: str) -> dict[str, dict]:
    """Pro Coin: FIFO-Ergebnis + Stammdaten (symbol/name). Auch geschlossene
    Positionen (quantity == 0) bleiben enthalten — wegen realized_pnl."""
    txs = store.list_for(user)
    out: dict[str, dict] = {}
    for coin_id, group in groupby(txs, key=lambda t: t["coin_id"]):
        rows = list(group)
        res = fifo.compute(rows)
        last = rows[-1]
        out[coin_id] = {
            "coin_id": coin_id,
            "symbol": last.get("symbol") or "",
            "name": last.get("name") or "",
            "quantity": res.quantity,
            "cost_basis": res.cost_basis,
            "avg_cost": res.avg_cost,
            "realized_pnl": res.realized_pnl,
            "invested": res.invested,
            "proceeds": res.proceeds,
        }
    return out


async def _prices(coin_ids: list[str]) -> dict[str, dict]:
    if not coin_ids:
        return {}
    try:
        rows = await client.markets(_VS, ids=coin_ids)
    except Exception:
        rows = []
    return {r["id"]: r for r in rows if r.get("id")}


async def summary(user: str) -> dict:
    """Vollständige Portfolio-Übersicht: Positionen + aggregierte Kennzahlen."""
    positions = _positions_from_ledger(user)
    held_ids = [cid for cid, p in positions.items() if p["quantity"] > _EPS]
    prices = await _prices(list(positions.keys()))

    out_positions: list[dict] = []
    total_value = 0.0
    total_cost = 0.0
    total_realized = 0.0
    total_unrealized = 0.0  # Summe nur der Positionen mit bekannter Cost-Basis

    for cid, p in positions.items():
        market = prices.get(cid) or {}
        price = market.get("price")
        qty = p["quantity"]
        value = (price or 0.0) * qty if qty > _EPS else 0.0
        cost = p["cost_basis"]
        # Unrealisierter G/V nur, wenn echte Einstandskosten bekannt sind. Bei
        # Cost-Basis 0 (z.B. reine Transfers ohne erfassten Kaufpreis) wäre
        # "value - 0" ein Fantasie-Gewinn in Höhe des vollen Werts → stattdessen
        # 0 (unbekannt). So zeigt das Portfolio den Wert, aber keinen Fake-Gewinn.
        has_cost = cost > _EPS
        unrealized = (value - cost) if (qty > _EPS and has_cost) else 0.0
        pct = (unrealized / cost * 100.0) if has_cost else 0.0

        total_value += value
        total_cost += cost
        total_unrealized += unrealized
        total_realized += p["realized_pnl"]

        out_positions.append({
            **p,
            "price": price,
            "image": market.get("image"),
            "change_24h": market.get("change_24h"),
            "value": value,
            "unrealized_pnl": unrealized,
            "unrealized_pct": pct,
            "is_open": qty > _EPS,
        })

    # Allocation (nur offene Positionen, relativ zum Gesamtwert).
    for p in out_positions:
        p["allocation"] = (p["value"] / total_value * 100.0) if total_value > _EPS else 0.0

    # Offene zuerst (nach Wert), dann geschlossene.
    out_positions.sort(key=lambda x: (not x["is_open"], -x["value"]))

    # total_unrealized ist bereits über die Positionen summiert (nur die mit
    # bekannter Cost-Basis). Prozent relativ zu den Kosten DIESER Positionen.
    total_pct = (total_unrealized / total_cost * 100.0) if total_cost > _EPS else 0.0

    return {
        "currency": _VS.upper(),
        "positions": out_positions,
        "totals": {
            "value": total_value,
            "cost_basis": total_cost,
            "unrealized_pnl": total_unrealized,
            "unrealized_pct": total_pct,
            "realized_pnl": total_realized,
            "open_count": len(held_ids),
            "position_count": len(out_positions),
        },
    }


async def coin_detail(user: str, coin_id: str) -> dict:
    """P&L-Detail eines einzelnen Coins inkl. zugrunde liegender Transaktionen."""
    txs = store.list_for(user, coin_id=coin_id)
    res = fifo.compute(txs)
    prices = await _prices([coin_id]) if res.quantity > _EPS else {}
    market = prices.get(coin_id) or {}
    price = market.get("price")
    value = (price or 0.0) * res.quantity
    # Wie in summary(): kein Fantasie-Gewinn bei Cost-Basis 0.
    unrealized = (value - res.cost_basis) if (res.quantity > _EPS and res.cost_basis > _EPS) else 0.0
    return {
        "coin_id": coin_id,
        "currency": _VS.upper(),
        "quantity": res.quantity,
        "avg_cost": res.avg_cost,
        "cost_basis": res.cost_basis,
        "price": price,
        "value": value,
        "unrealized_pnl": unrealized,
        "realized_pnl": res.realized_pnl,
        "invested": res.invested,
        "proceeds": res.proceeds,
        "transactions": txs,
    }
