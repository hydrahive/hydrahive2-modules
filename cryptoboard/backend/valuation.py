"""Wertverlauf-Berechnung — reine Logik, keine DB/kein Netz.

Aus dem Transaktions-Ledger + historischen Tageskursen wird die tägliche
Portfolio-Wertreihe (EUR) gebildet. Nur Marktwert, kein P&L (alle Coins aus
Mining → kein Einstandspreis).

Kernschritte:
  1. daily_holdings: pro Coin die kumulative Restmenge je Tag (Σ Zugänge −
     Σ Abgänge bis zu diesem Tag, auf 0 begrenzt — wie der FIFO-Bestand).
  2. value_series: über die Zeitachse (erste Tx … heute) je Tag
     Σ (Bestand[coin] × Kurs[coin]); fehlende Kurse forward-fillen.
"""
from __future__ import annotations

from datetime import date, timedelta

_IN = {"buy", "transfer_in"}
_OUT = {"sell", "transfer_out"}
_EPS = 1e-12


def _day_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def daily_deltas(transactions: list[dict]) -> dict[str, dict[str, float]]:
    """Pro Coin die Mengen-Änderung je Tag: {coin_id: {day: delta}}.

    delta > 0 Zugang, < 0 Abgang. executed_at wird auf den Tag (erste 10
    Zeichen, YYYY-MM-DD) reduziert.
    """
    out: dict[str, dict[str, float]] = {}
    for tx in transactions:
        kind = tx.get("kind")
        qty = float(tx.get("quantity") or 0.0)
        if qty <= _EPS:
            continue
        if kind in _IN:
            signed = qty
        elif kind in _OUT:
            signed = -qty
        else:
            continue
        coin = tx.get("coin_id") or ""
        day = str(tx.get("executed_at") or "")[:10]
        if not coin or len(day) != 10:
            continue
        out.setdefault(coin, {})
        out[coin][day] = out[coin].get(day, 0.0) + signed
    return out


def _date_range(start: str, end: str) -> list[str]:
    """Alle ISO-Tage von start..end inklusive."""
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    days: list[str] = []
    cur = d0
    while cur <= d1:
        days.append(_day_str(cur))
        cur += timedelta(days=1)
    return days


def _price_on(series: dict[str, float], day: str, last: float | None) -> float | None:
    """Kurs am Tag, sonst forward-fill (letzter bekannter Kurs)."""
    if day in series:
        return series[day]
    return last


def value_series(
    transactions: list[dict],
    prices: dict[str, dict[str, float]],
    today: str,
) -> list[dict]:
    """Tägliche Portfolio-Wertreihe [{day, value}] von der ersten Transaktion
    bis `today`. `prices` = {coin_id: {day: price}}.
    """
    deltas = daily_deltas(transactions)
    if not deltas:
        return []

    all_tx_days = [d for coin in deltas.values() for d in coin]
    start = min(all_tx_days)
    if start > today:
        return []
    timeline = _date_range(start, today)

    coins = list(deltas.keys())
    holding = {c: 0.0 for c in coins}          # laufender Bestand
    last_price = {c: None for c in coins}       # für forward-fill

    out: list[dict] = []
    for day in timeline:
        total = 0.0
        for c in coins:
            # Bestand fortschreiben
            if day in deltas[c]:
                holding[c] = max(0.0, holding[c] + deltas[c][day])
            price = _price_on(prices.get(c, {}), day, last_price[c])
            if price is not None:
                last_price[c] = price
            if holding[c] > _EPS and price is not None:
                total += holding[c] * price
        out.append({"day": day, "value": total})
    return out


def stats_from_series(series: list[dict]) -> dict:
    """Kennzahlen aus der Wertreihe: aktueller Wert, ATH (+Tag), Änderung
    24h/7d/30d/1J (absolut + %)."""
    if not series:
        return {
            "current": 0.0, "ath": {"value": 0.0, "day": None},
            "change_24h": _delta(0, 0), "change_7d": _delta(0, 0),
            "change_30d": _delta(0, 0), "change_1y": _delta(0, 0),
        }
    current = series[-1]["value"]
    ath = max(series, key=lambda p: p["value"])

    def at_offset(days_back: int) -> float:
        idx = len(series) - 1 - days_back
        return series[idx]["value"] if idx >= 0 else series[0]["value"]

    return {
        "current": current,
        "ath": {"value": ath["value"], "day": ath["day"]},
        "change_24h": _delta(current, at_offset(1)),
        "change_7d": _delta(current, at_offset(7)),
        "change_30d": _delta(current, at_offset(30)),
        "change_1y": _delta(current, at_offset(365)),
    }


def _delta(now: float, then: float) -> dict:
    abs_change = now - then
    pct = (abs_change / then * 100.0) if then > _EPS else 0.0
    return {"abs": abs_change, "pct": pct}
