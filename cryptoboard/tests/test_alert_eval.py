"""Alert-Crossing-Logik — reine Funktionen (keine DB)."""
from __future__ import annotations

from backend import alert_eval as ev


# ---------------------------------------------------------------- should_fire
def test_erste_beobachtung_feuert_nie():
    assert ev.should_fire("price_above", 100, 150, None) is False
    assert ev.should_fire("price_below", 100, 50, None) is False


def test_above_feuert_nur_am_uebertritt():
    # vorher 90 (unter 100), jetzt 110 (über) → feuert
    assert ev.should_fire("price_above", 100, 110, 90) is True
    # bereits drüber geblieben → kein erneutes Feuern
    assert ev.should_fire("price_above", 100, 120, 110) is False
    # immer drunter → nein
    assert ev.should_fire("price_above", 100, 95, 90) is False


def test_below_feuert_nur_am_uebertritt():
    assert ev.should_fire("price_below", 100, 90, 110) is True
    assert ev.should_fire("price_below", 100, 80, 90) is False
    assert ev.should_fire("price_below", 100, 105, 110) is False


def test_exakt_auf_schwelle_zaehlt_als_above():
    # value == threshold, vorher drunter → Übertritt nach oben
    assert ev.should_fire("price_above", 100, 100, 99) is True


def test_portfolio_und_pct_nutzen_gleiche_logik():
    assert ev.should_fire("portfolio_above", 10000, 10500, 9500) is True
    assert ev.should_fire("pct_change_24h_below", -5, -6, -4) is True
    assert ev.should_fire("pct_change_24h_above", 5, 6, 4) is True


def test_unbekanntes_kind_feuert_nicht():
    assert ev.should_fire("nonsense", 1, 2, 0) is False


# ---------------------------------------------------------------- current_value
def test_current_value_routing():
    assert ev.current_value("price_above", price=42, change_24h=1, portfolio_value=999) == 42
    assert ev.current_value("pct_change_24h_below", price=42, change_24h=1, portfolio_value=999) == 1
    assert ev.current_value("portfolio_above", price=42, change_24h=1, portfolio_value=999) == 999
    assert ev.current_value("price_above", price=None, change_24h=1, portfolio_value=9) is None


# ---------------------------------------------------------------- format_message
def test_format_message_enthaelt_symbol_und_werte():
    msg = ev.format_message("price_above", "BTC", 100000, 105000)
    assert "BTC" in msg and "≥" in msg
    msg2 = ev.format_message("portfolio_below", "", 10000, 9000)
    assert "Portfolio" in msg2 and "≤" in msg2
    msg3 = ev.format_message("pct_change_24h_above", "ETH", 5, 7.5)
    assert "%" in msg3
