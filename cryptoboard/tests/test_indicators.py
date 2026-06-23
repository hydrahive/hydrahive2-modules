"""Indikator-Engine — reine Berechnungen (keine DB, kein Netz)."""
from __future__ import annotations

import pytest

from backend import indicators as ind


def test_sma_basic():
    out = ind.sma([1, 2, 3, 4, 5], 3)
    assert out[0] is None and out[1] is None
    assert out[2] == pytest.approx(2.0)   # (1+2+3)/3
    assert out[3] == pytest.approx(3.0)   # (2+3+4)/3
    assert out[4] == pytest.approx(4.0)   # (3+4+5)/3


def test_sma_kurze_reihe_alles_none():
    assert ind.sma([1, 2], 5) == [None, None]


def test_ema_seed_ist_sma():
    prices = [1, 2, 3, 4, 5, 6]
    out = ind.ema(prices, 3)
    assert out[0] is None and out[1] is None
    assert out[2] == pytest.approx(2.0)   # Seed = SMA(1,2,3)
    # k = 2/4 = 0.5; out[3] = 4*0.5 + 2*0.5 = 3.0
    assert out[3] == pytest.approx(3.0)
    assert out[4] == pytest.approx(4.0)


def test_rsi_steigende_reihe_nahe_100():
    prices = [float(i) for i in range(1, 20)]  # streng monoton steigend
    out = ind.rsi(prices, 14)
    # nur Gewinne, keine Verluste → RSI = 100
    assert out[14] == pytest.approx(100.0)


def test_rsi_fallende_reihe_nahe_0():
    prices = [float(i) for i in range(20, 1, -1)]  # streng fallend
    out = ind.rsi(prices, 14)
    assert out[14] == pytest.approx(0.0)


def test_rsi_ausrichtung():
    prices = [float(i) for i in range(1, 20)]
    out = ind.rsi(prices, 14)
    # erste 14 Werte (Index 0..13) None, ab 14 berechnet
    assert all(v is None for v in out[:14])
    assert out[14] is not None


def test_rsi_kurze_reihe():
    assert ind.rsi([1, 2, 3], 14) == [None, None, None]


def test_macd_struktur_und_laenge():
    prices = [float(i % 7) + i * 0.1 for i in range(60)]
    m = ind.macd(prices)
    assert set(m.keys()) == {"macd", "signal", "histogram"}
    assert len(m["macd"]) == len(prices)
    assert len(m["signal"]) == len(prices)
    # MACD ab Index 25 (slow=26 → 25) definiert
    assert m["macd"][25] is not None
    assert m["macd"][24] is None


def test_macd_histogram_ist_macd_minus_signal():
    prices = [float(i) for i in range(60)]
    m = ind.macd(prices)
    for mc, sg, hi in zip(m["macd"], m["signal"], m["histogram"]):
        if mc is not None and sg is not None:
            assert hi == pytest.approx(mc - sg)
        else:
            assert hi is None


def test_compute_all_keys():
    prices = [float(i) for i in range(100)]
    out = ind.compute_all(prices)
    assert set(out.keys()) == {
        "sma20", "sma50", "ema12", "ema26", "rsi14",
        "macd", "macd_signal", "macd_histogram",
    }
    assert all(len(v) == len(prices) for v in out.values())
