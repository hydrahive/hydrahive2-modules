"""FIFO-Cost-Basis-Engine — reine Funktionen, keine DB, kein Netz.

Rechnet aus einer chronologischen Transaktionsliste eines einzelnen Coins die
aktuelle Restmenge, die FIFO-Cost-Basis der noch gehaltenen Lots und den bisher
realisierten Gewinn/Verlust aus. Alle Geldwerte in EUR.

Transaktions-Arten:
  buy / transfer_in   → öffnet ein Lot (Menge, Stückkosten inkl. anteiliger Fee)
  sell / transfer_out → baut Lots in FIFO-Reihenfolge ab (ältestes zuerst)

`transfer_in` ohne Preis (price=0) legt ein Lot mit Kostenbasis 0 an — der Coin
gilt dann beim späteren Verkauf voll als Gewinn. Wer eine echte Kostenbasis für
eingehende Transfers will, trägt einen price ein.

Reihenfolge: Der Aufrufer übergibt die Transaktionen bereits nach executed_at
(dann id) aufsteigend sortiert. Diese Reihenfolge IST die FIFO-Reihenfolge.
"""
from __future__ import annotations

from dataclasses import dataclass

_OPEN = {"buy", "transfer_in"}
_CLOSE = {"sell", "transfer_out"}
_EPS = 1e-12


@dataclass
class Lot:
    """Ein offenes Kauf-Lot: Restmenge und Stückkosten (EUR, inkl. anteiliger Fee)."""

    quantity: float
    unit_cost: float


@dataclass
class CoinResult:
    """Ergebnis der FIFO-Auswertung eines Coins."""

    quantity: float          # aktuell gehaltene Restmenge
    cost_basis: float        # Gesamtkosten der offenen Lots (EUR)
    avg_cost: float          # gewichtete Stückkosten der offenen Lots (EUR), 0 bei leer
    realized_pnl: float      # bisher realisierter Gewinn/Verlust (EUR)
    invested: float          # Summe aller Kauf-Kosten inkl. Fees (EUR), brutto
    proceeds: float          # Summe aller Verkaufs-Erlöse abzgl. Fees (EUR)


def _open_lot(qty: float, price: float, fee: float) -> Lot:
    # Anteilige Fee auf die Stückkosten umlegen (Fee verteuert den Einstand).
    total_cost = qty * price + fee
    unit = total_cost / qty if qty > _EPS else 0.0
    return Lot(quantity=qty, unit_cost=unit)


def compute(transactions: list[dict], *, strict: bool = False) -> CoinResult:
    """Wertet die (chronologisch sortierten) Transaktionen EINES Coins aus.

    strict=True  → wirft ValueError('insufficient_holdings'), wenn ein Verkauf/
                   Transfer-out mehr abbaut als vorhanden. Für die manuelle
                   Einzel-Erfassung, wo der User den vollen Kontext hat.
    strict=False → toleranter Anzeige-Modus (Default): ein Abgang ohne (genug)
                   Bestand wird auf den vorhandenen Bestand begrenzt; die
                   überschüssige Menge gilt als Realisierung gegen Cost-Basis 0.
                   So bricht die Portfolio-Anzeige nie an unvollständigen
                   Ledgern (z.B. CSV-Import nur von Auszahlungen, deren Käufe
                   in einer anderen, nicht importierten Quelle lagen).
    """
    lots: list[Lot] = []
    realized = 0.0
    invested = 0.0
    proceeds = 0.0
    total_in = 0.0   # Summe aller Zugänge (Menge)
    total_out = 0.0  # Summe aller Abgänge (Menge)

    for tx in transactions:
        kind = tx["kind"]
        qty = float(tx["quantity"])
        price = float(tx.get("price") or 0.0)
        fee = float(tx.get("fee") or 0.0)
        if qty <= _EPS:
            continue

        if kind in _OPEN:
            total_in += qty
            lots.append(_open_lot(qty, price, fee))
            invested += qty * price + fee
        elif kind in _CLOSE:
            total_out += qty
            remaining = qty
            sale_proceeds = qty * price - fee
            proceeds += sale_proceeds
            # Erlös je Stück (Fee anteilig abgezogen) für die realisierte P&L.
            unit_proceed = sale_proceeds / qty if qty > _EPS else 0.0
            while remaining > _EPS:
                if not lots:
                    if strict:
                        raise ValueError("insufficient_holdings")
                    # Tolerant: Rest gegen Cost-Basis 0 realisieren, Bestand
                    # bleibt bei 0 (keine Negativ-Position).
                    realized += remaining * unit_proceed
                    break
                lot = lots[0]
                take = min(lot.quantity, remaining)
                realized += take * (unit_proceed - lot.unit_cost)
                lot.quantity -= take
                remaining -= take
                if lot.quantity <= _EPS:
                    lots.pop(0)
        # unbekannte kinds werden ignoriert (Validierung passiert im Store/Route)

    lot_quantity = sum(l.quantity for l in lots)
    cost_basis = sum(l.quantity * l.unit_cost for l in lots)

    if strict:
        # Strikt: Bestand == verbliebene Lots (Reihenfolge garantiert korrekt).
        quantity = lot_quantity
    else:
        # Tolerant (Anzeige): Mengen-Bilanz ist immer Zugänge − Abgänge, auf 0
        # begrenzt. Unabhängig von FIFO-Reihenfolge — so summieren sich Ein-/
        # Auszahlungen eines Wallet-Verlaufs korrekt, auch bei unvollständigem
        # oder unsortiertem Ledger. Die Cost-Basis bleibt aus den realen Lots
        # (kann nicht aus Transfer-Daten ohne Preis rekonstruiert werden).
        quantity = max(0.0, total_in - total_out)

    avg_cost = cost_basis / quantity if (quantity > _EPS and cost_basis > _EPS) else 0.0

    return CoinResult(
        quantity=quantity,
        cost_basis=cost_basis,
        avg_cost=avg_cost,
        realized_pnl=realized,
        invested=invested,
        proceeds=proceeds,
    )
