"""Wertverlauf-Engine — reine Logik (keine DB/kein Netz)."""
from __future__ import annotations

import pytest

from backend import valuation as v


def _tx(coin, kind, qty, day):
    return {"coin_id": coin, "kind": kind, "quantity": qty, "executed_at": day}


# ---------------------------------------------------------------- daily_deltas
def test_daily_deltas_summiert_pro_tag():
    txs = [
        _tx("bitcoin", "transfer_in", 1.0, "2020-01-01"),
        _tx("bitcoin", "transfer_in", 0.5, "2020-01-01"),  # selber Tag
        _tx("bitcoin", "transfer_out", 0.2, "2020-02-01"),
    ]
    d = v.daily_deltas(txs)
    assert d["bitcoin"]["2020-01-01"] == pytest.approx(1.5)
    assert d["bitcoin"]["2020-02-01"] == pytest.approx(-0.2)


def test_daily_deltas_datum_gekuerzt():
    txs = [_tx("tron", "transfer_in", 100, "2021-05-05T13:22:00+0000")]
    d = v.daily_deltas(txs)
    assert "2021-05-05" in d["tron"]


def test_daily_deltas_ignoriert_unbekannte_kinds():
    txs = [{"coin_id": "x", "kind": "weird", "quantity": 5, "executed_at": "2020-01-01"}]
    assert v.daily_deltas(txs) == {}


# ---------------------------------------------------------------- value_series
def test_value_series_einfach():
    # 1 BTC am 2020-01-01 rein, Kurs konstant 100
    txs = [_tx("bitcoin", "transfer_in", 1.0, "2020-01-01")]
    prices = {"bitcoin": {"2020-01-01": 100.0, "2020-01-02": 110.0, "2020-01-03": 120.0}}
    series = v.value_series(txs, prices, "2020-01-03")
    assert len(series) == 3
    assert series[0] == {"day": "2020-01-01", "value": pytest.approx(100.0)}
    assert series[1]["value"] == pytest.approx(110.0)
    assert series[2]["value"] == pytest.approx(120.0)


def test_value_series_forward_fill():
    # Kurs nur an Tag 1 bekannt → Tag 2/3 nutzen letzten Kurs
    txs = [_tx("bitcoin", "transfer_in", 2.0, "2020-01-01")]
    prices = {"bitcoin": {"2020-01-01": 50.0}}
    series = v.value_series(txs, prices, "2020-01-03")
    assert series[0]["value"] == pytest.approx(100.0)
    assert series[1]["value"] == pytest.approx(100.0)  # forward-filled
    assert series[2]["value"] == pytest.approx(100.0)


def test_value_series_abgang_reduziert_wert():
    txs = [
        _tx("tron", "transfer_in", 1000.0, "2020-01-01"),
        _tx("tron", "transfer_out", 400.0, "2020-01-02"),
    ]
    prices = {"tron": {"2020-01-01": 0.02, "2020-01-02": 0.02}}
    series = v.value_series(txs, prices, "2020-01-02")
    assert series[0]["value"] == pytest.approx(20.0)   # 1000 * 0.02
    assert series[1]["value"] == pytest.approx(12.0)   # 600 * 0.02


def test_value_series_mehrere_coins():
    txs = [
        _tx("bitcoin", "transfer_in", 1.0, "2020-01-01"),
        _tx("tron", "transfer_in", 1000.0, "2020-01-01"),
    ]
    prices = {
        "bitcoin": {"2020-01-01": 100.0},
        "tron": {"2020-01-01": 0.05},
    }
    series = v.value_series(txs, prices, "2020-01-01")
    assert series[0]["value"] == pytest.approx(150.0)  # 100 + 50


def test_value_series_leer_ohne_transaktionen():
    assert v.value_series([], {}, "2020-01-01") == []


def test_value_series_altbestand_vor_kursfenster():
    # Coins von 2018 (vor verfügbarem Kursfenster), Kurse erst ab 2024.
    # Die Kurve startet beim ersten Kurstag MIT dem korrekten Altbestand.
    txs = [
        _tx("tron", "transfer_in", 100.0, "2018-05-01"),
        _tx("tron", "transfer_in", 50.0, "2024-06-02"),
    ]
    prices = {"tron": {"2024-06-01": 0.10, "2024-06-02": 0.12, "2024-06-03": 0.11}}
    series = v.value_series(txs, prices, "2024-06-03")
    assert series[0] == {"day": "2024-06-01", "value": pytest.approx(10.0)}   # 100 * 0.10
    assert series[1]["value"] == pytest.approx(18.0)                          # 150 * 0.12
    assert series[2]["value"] == pytest.approx(16.5)                          # 150 * 0.11


def test_value_series_kein_doppelzaehlen_am_start():
    # Ein Delta GENAU am Start-Tag darf nicht zusätzlich zum Vor-Start-Bestand
    # doppelt gezählt werden.
    txs = [
        _tx("tron", "transfer_in", 100.0, "2018-01-01"),  # vor Start
        _tx("tron", "transfer_in", 10.0, "2024-06-01"),   # am Start-Tag
    ]
    prices = {"tron": {"2024-06-01": 1.0}}
    series = v.value_series(txs, prices, "2024-06-01")
    assert series[0]["value"] == pytest.approx(110.0)  # 100 + 10, nicht 210


def test_value_series_coin_ohne_kurs_traegt_nichts_bei():
    txs = [_tx("obscure", "transfer_in", 10.0, "2020-01-01")]
    series = v.value_series(txs, {}, "2020-01-02")
    assert all(p["value"] == 0.0 for p in series)


# ---------------------------------------------------------------- stats
def test_stats_ath_und_current():
    series = [
        {"day": "2020-01-01", "value": 100.0},
        {"day": "2020-01-02", "value": 250.0},  # ATH
        {"day": "2020-01-03", "value": 180.0},
    ]
    s = v.stats_from_series(series)
    assert s["current"] == pytest.approx(180.0)
    assert s["ath"]["value"] == pytest.approx(250.0)
    assert s["ath"]["day"] == "2020-01-02"


def test_stats_change_24h():
    series = [{"day": "2020-01-01", "value": 100.0}, {"day": "2020-01-02", "value": 150.0}]
    s = v.stats_from_series(series)
    assert s["change_24h"]["abs"] == pytest.approx(50.0)
    assert s["change_24h"]["pct"] == pytest.approx(50.0)


def test_stats_leere_serie():
    s = v.stats_from_series([])
    assert s["current"] == 0.0
    assert s["ath"]["day"] is None
