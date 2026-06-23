"""FIFO-Engine — reine Cost-Basis-Berechnung (keine DB, kein Netz)."""
from __future__ import annotations

import pytest

from backend import fifo


def _tx(kind, qty, price=0.0, fee=0.0):
    return {"kind": kind, "quantity": qty, "price": price, "fee": fee}


def test_leeres_ledger():
    r = fifo.compute([])
    assert r.quantity == 0
    assert r.cost_basis == 0
    assert r.realized_pnl == 0


def test_einfacher_kauf():
    r = fifo.compute([_tx("buy", 2, 100.0)])
    assert r.quantity == 2
    assert r.cost_basis == pytest.approx(200.0)
    assert r.avg_cost == pytest.approx(100.0)
    assert r.realized_pnl == 0
    assert r.invested == pytest.approx(200.0)


def test_kauf_mit_fee_erhoeht_einstand():
    r = fifo.compute([_tx("buy", 1, 100.0, fee=10.0)])
    assert r.avg_cost == pytest.approx(110.0)
    assert r.cost_basis == pytest.approx(110.0)


def test_fifo_teilverkauf_ueber_zwei_lots():
    # Lot1: 1 @ 100, Lot2: 1 @ 200. Verkauf 1.5 @ 300.
    txs = [
        _tx("buy", 1, 100.0),
        _tx("buy", 1, 200.0),
        _tx("sell", 1.5, 300.0),
    ]
    r = fifo.compute(txs)
    # Verkauft: 1.0 aus Lot1 (Kosten 100) + 0.5 aus Lot2 (Kosten 100) = 200 Kosten
    # Erlös: 1.5 * 300 = 450 → realized = 450 - 200 = 250
    assert r.realized_pnl == pytest.approx(250.0)
    # Rest: 0.5 aus Lot2 @ 200
    assert r.quantity == pytest.approx(0.5)
    assert r.cost_basis == pytest.approx(100.0)
    assert r.avg_cost == pytest.approx(200.0)


def test_kompletter_verkauf_schliesst_position():
    txs = [_tx("buy", 1, 100.0), _tx("sell", 1, 150.0)]
    r = fifo.compute(txs)
    assert r.quantity == pytest.approx(0.0)
    assert r.cost_basis == pytest.approx(0.0)
    assert r.realized_pnl == pytest.approx(50.0)


def test_verkauf_mit_fee_mindert_erloes():
    txs = [_tx("buy", 1, 100.0), _tx("sell", 1, 150.0, fee=10.0)]
    r = fifo.compute(txs)
    # Erlös 150 - 10 Fee = 140, Kosten 100 → realized 40
    assert r.realized_pnl == pytest.approx(40.0)


def test_verkauf_ueber_bestand_wirft():
    with pytest.raises(ValueError, match="insufficient_holdings"):
        fifo.compute([_tx("buy", 1, 100.0), _tx("sell", 2, 150.0)])


def test_transfer_in_ohne_preis_ist_gewinn_beim_verkauf():
    txs = [_tx("transfer_in", 1, 0.0), _tx("sell", 1, 100.0)]
    r = fifo.compute(txs)
    assert r.realized_pnl == pytest.approx(100.0)


def test_transfer_out_baut_lot_ab():
    txs = [_tx("buy", 2, 100.0), _tx("transfer_out", 1, 0.0)]
    r = fifo.compute(txs)
    assert r.quantity == pytest.approx(1.0)
    # transfer_out @ 0 → realized = 0 - cost(100) = -100 (Abgang ohne Erlös)
    assert r.realized_pnl == pytest.approx(-100.0)


def test_realistische_sequenz():
    txs = [
        _tx("buy", 0.5, 20000.0),       # 10000
        _tx("buy", 0.5, 30000.0),       # 15000
        _tx("sell", 0.5, 40000.0),      # Erlös 20000, Kosten Lot1 10000 → +10000
        _tx("buy", 0.25, 25000.0),      # 6250
    ]
    r = fifo.compute(txs)
    assert r.realized_pnl == pytest.approx(10000.0)
    # Rest: 0.5 @ 30000 + 0.25 @ 25000 = 0.75 menge, cost 15000+6250=21250
    assert r.quantity == pytest.approx(0.75)
    assert r.cost_basis == pytest.approx(21250.0)
