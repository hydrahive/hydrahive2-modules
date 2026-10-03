"""Ertragsrechnung — reine Funktionen, kein I/O.

Grundlage (docs/specs/mining-modul.md, verifiziert 03.10.2026):
``estimated_profit_day`` von Kryptex = Coins je H/s und Tag, nach Pool-Gebühr.
Liefert Kryptex den Wert nicht (PROP-Coins), rechnen wir ihn selbst aus
Tagesausschüttung / Netz-Hashrate × (1 − Gebühr). Für RVN weicht das < 2 %
von Kryptex ab.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoinQuote:
    """Normalisierte Pool-/Kursdaten eines Coins (Stand eines Abrufs)."""
    coin: str
    name: str
    algo: str
    fee: float
    fee_type: str
    profit_per_hs_day: float | None  # Coins je H/s und Tag (nach Gebühr)
    price_usd: float | None
    estimated: bool = False  # True = selbst gerechnet statt von Kryptex


def coins_per_hs_day(
    *, kryptex_value: float | None, daily_emission: float | None,
    net_hashrate: float | None, fee: float,
) -> tuple[float | None, bool]:
    """(Coins je H/s und Tag, selbst_gerechnet). None wenn nicht bestimmbar."""
    if kryptex_value is not None and kryptex_value > 0:
        return float(kryptex_value), False
    if daily_emission and net_hashrate and daily_emission > 0 and net_hashrate > 0:
        return daily_emission / net_hashrate * (1.0 - fee), True
    return None, False


def usd_per_day(quote: CoinQuote, hashrate: float, *, prop_discount: float = 0.0) -> float | None:
    """Ertrag in USD/Tag für eine Hashrate (H/s). PROP-Coins mit Abschlag."""
    if quote.profit_per_hs_day is None or quote.price_usd is None or hashrate <= 0:
        return None
    value = quote.profit_per_hs_day * hashrate * quote.price_usd
    if quote.fee_type.upper() == "PROP" and prop_discount > 0:
        value *= max(0.0, 1.0 - prop_discount)
    return value


def rank(
    quotes: list[CoinQuote], hashrates: dict[str, float], *, prop_discount: float = 0.0,
) -> list[tuple[CoinQuote, float]]:
    """Coins nach USD/Tag absteigend. Ohne Hashrate oder Kurs → weggelassen."""
    rows: list[tuple[CoinQuote, float]] = []
    for q in quotes:
        hr = hashrates.get(q.coin)
        if not hr:
            continue
        usd = usd_per_day(q, hr, prop_discount=prop_discount)
        if usd is not None:
            rows.append((q, usd))
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows
