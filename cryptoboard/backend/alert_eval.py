"""Alert-Auswertung — reine Crossing-Logik, keine I/O.

Entscheidet, ob ein Alert bei einem neuen Messwert auslösen soll. Crossing-
Semantik: feuert nur beim Übertritt der Schwelle (Wechsel von „nicht erfüllt"
zu „erfüllt"), nicht in jedem Tick darüber/darunter. Der vorige Wert
(last_value) kommt aus dem Store; ist er None (erste Beobachtung), wird NICHT
gefeuert — wir kennen die Richtung des Übertritts noch nicht.
"""
from __future__ import annotations

_ABOVE = ("price_above", "pct_change_24h_above", "portfolio_above")
_BELOW = ("price_below", "pct_change_24h_below", "portfolio_below")


def _is_above(value: float, threshold: float) -> bool:
    return value >= threshold


def should_fire(kind: str, threshold: float, value: float, last_value: float | None) -> bool:
    """True genau dann, wenn `value` die Schwelle in dieser Aktualisierung
    in der vom kind vorgegebenen Richtung neu überschreitet."""
    if last_value is None:
        return False
    if kind in _ABOVE:
        # vorher unter Schwelle, jetzt darüber
        return last_value < threshold <= value
    if kind in _BELOW:
        # vorher über Schwelle, jetzt darunter
        return last_value > threshold >= value
    return False


def current_value(kind: str, *, price: float | None, change_24h: float | None,
                  portfolio_value: float | None) -> float | None:
    """Liefert den für das Alert-kind relevanten Messwert."""
    if kind in ("price_above", "price_below"):
        return price
    if kind in ("pct_change_24h_above", "pct_change_24h_below"):
        return change_24h
    if kind in ("portfolio_above", "portfolio_below"):
        return portfolio_value
    return None


def format_message(kind: str, symbol: str, threshold: float, value: float) -> str:
    """Kurzer, menschenlesbarer Benachrichtigungstext (EUR / %)."""
    sym = symbol or "Portfolio"
    if kind in ("price_above", "price_below"):
        arrow = "≥" if kind == "price_above" else "≤"
        return f"{sym}: Kurs {value:,.2f} € {arrow} {threshold:,.2f} €"
    if kind in ("pct_change_24h_above", "pct_change_24h_below"):
        arrow = "≥" if kind.endswith("above") else "≤"
        return f"{sym}: 24h-Änderung {value:+.2f} % {arrow} {threshold:+.2f} %"
    # portfolio_*
    arrow = "≥" if kind == "portfolio_above" else "≤"
    return f"Portfolio-Wert {value:,.2f} € {arrow} {threshold:,.2f} €"
