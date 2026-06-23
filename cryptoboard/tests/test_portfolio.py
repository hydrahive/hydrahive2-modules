"""C4 — Portfolio: Trade-Log-CRUD, FIFO-P&L-Durchstich, per-User-Isolation.

CoinGecko-Client (markets) wird gemockt — kein echter Netz-Traffic.
"""
from __future__ import annotations

import pytest

from backend import client as cg

PREFIX = "/api/modules/cryptoboard"


@pytest.fixture
def other_headers(client):
    r = client.post("/api/auth/login", json={"username": "other", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _mock_markets(monkeypatch):
    """Statische Preise: bitcoin=50000, ethereum=3000 EUR."""
    async def fake_markets(vs, *, ids=None, top=None):
        prices = {
            "bitcoin": {"id": "bitcoin", "price": 50000.0, "image": "btc.png", "change_24h": 1.5},
            "ethereum": {"id": "ethereum", "price": 3000.0, "image": "eth.png", "change_24h": -2.0},
        }
        return [prices[i] for i in (ids or []) if i in prices]

    monkeypatch.setattr(cg, "markets", fake_markets)


def _buy(coin="bitcoin", qty=1.0, price=40000.0, at="2026-01-01", **kw):
    return {"coin_id": coin, "symbol": coin[:3], "name": coin.title(),
            "kind": "buy", "quantity": qty, "price": price, "executed_at": at, **kw}


# ---------------------------------------------------------------- Auth + CRUD
def test_portfolio_braucht_auth(client):
    assert client.get(f"{PREFIX}/portfolio").status_code == 401
    assert client.get(f"{PREFIX}/portfolio/transactions").status_code == 401


def test_add_list_delete_transaction(client, auth_headers):
    assert client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json() == []

    r = client.post(f"{PREFIX}/portfolio/transactions", json=_buy(), headers=auth_headers)
    assert r.status_code == 200
    tx_id = r.json()["id"]

    txs = client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json()
    assert len(txs) == 1
    assert txs[0]["coin_id"] == "bitcoin"
    assert txs[0]["symbol"] == "BIT"  # upper-cased

    assert client.delete(f"{PREFIX}/portfolio/transactions/{tx_id}", headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json() == []


def test_update_transaction(client, auth_headers):
    tx_id = client.post(f"{PREFIX}/portfolio/transactions", json=_buy(qty=1.0), headers=auth_headers).json()["id"]
    upd = _buy(qty=2.0, price=45000.0)
    r = client.patch(f"{PREFIX}/portfolio/transactions/{tx_id}", json=upd, headers=auth_headers)
    assert r.status_code == 200
    txs = client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json()
    assert txs[0]["quantity"] == 2.0
    assert txs[0]["price"] == 45000.0


def test_update_unknown_404(client, auth_headers):
    assert client.patch(f"{PREFIX}/portfolio/transactions/9999", json=_buy(), headers=auth_headers).status_code == 404


def test_delete_unknown_404(client, auth_headers):
    assert client.delete(f"{PREFIX}/portfolio/transactions/9999", headers=auth_headers).status_code == 404


# ---------------------------------------------------------------- Validierung
def test_invalid_coin_id(client, auth_headers):
    bad = _buy(coin="Invalid Id!")
    assert client.post(f"{PREFIX}/portfolio/transactions", json=bad, headers=auth_headers).status_code == 400


def test_invalid_kind(client, auth_headers):
    bad = _buy()
    bad["kind"] = "hodl"
    assert client.post(f"{PREFIX}/portfolio/transactions", json=bad, headers=auth_headers).status_code == 400


def test_invalid_date(client, auth_headers):
    bad = _buy(at="gestern")
    assert client.post(f"{PREFIX}/portfolio/transactions", json=bad, headers=auth_headers).status_code == 400


def test_negative_quantity_rejected(client, auth_headers):
    bad = _buy(qty=-1.0)
    assert client.post(f"{PREFIX}/portfolio/transactions", json=bad, headers=auth_headers).status_code == 422


# ---------------------------------------------------------------- P&L-Durchstich
def test_portfolio_summary_unrealized_pnl(client, auth_headers):
    # 1 BTC @ 40000 gekauft, Live 50000 → +10000 unrealisiert
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(qty=1.0, price=40000.0), headers=auth_headers)
    data = client.get(f"{PREFIX}/portfolio", headers=auth_headers).json()
    assert data["currency"] == "EUR"
    assert data["totals"]["value"] == pytest.approx(50000.0)
    assert data["totals"]["cost_basis"] == pytest.approx(40000.0)
    assert data["totals"]["unrealized_pnl"] == pytest.approx(10000.0)
    pos = data["positions"][0]
    assert pos["coin_id"] == "bitcoin"
    assert pos["allocation"] == pytest.approx(100.0)


def test_portfolio_realized_pnl_fifo(client, auth_headers):
    # Kauf 2 @ 40000, Verkauf 1 @ 50000 → realized = 50000-40000 = 10000
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(qty=2.0, price=40000.0, at="2026-01-01"), headers=auth_headers)
    sell = _buy(qty=1.0, price=50000.0, at="2026-02-01")
    sell["kind"] = "sell"
    client.post(f"{PREFIX}/portfolio/transactions", json=sell, headers=auth_headers)
    data = client.get(f"{PREFIX}/portfolio", headers=auth_headers).json()
    assert data["totals"]["realized_pnl"] == pytest.approx(10000.0)
    # Rest 1 BTC, Wert 50000, Kosten 40000 → unrealized 10000
    assert data["totals"]["unrealized_pnl"] == pytest.approx(10000.0)


def test_portfolio_allocation_two_coins(client, auth_headers):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(coin="bitcoin", qty=1.0, price=40000.0), headers=auth_headers)
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(coin="ethereum", qty=10.0, price=2000.0), headers=auth_headers)
    data = client.get(f"{PREFIX}/portfolio", headers=auth_headers).json()
    # BTC 50000, ETH 30000 → total 80000
    assert data["totals"]["value"] == pytest.approx(80000.0)
    alloc = {p["coin_id"]: p["allocation"] for p in data["positions"]}
    assert alloc["bitcoin"] == pytest.approx(62.5)
    assert alloc["ethereum"] == pytest.approx(37.5)


def test_coin_detail(client, auth_headers):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(qty=2.0, price=40000.0), headers=auth_headers)
    data = client.get(f"{PREFIX}/portfolio/coin/bitcoin", headers=auth_headers).json()
    assert data["quantity"] == pytest.approx(2.0)
    assert data["avg_cost"] == pytest.approx(40000.0)
    assert data["value"] == pytest.approx(100000.0)
    assert len(data["transactions"]) == 1


def test_portfolio_nur_abgaenge_crasht_nicht(client, auth_headers):
    """Regression: CSV-Import nur von Auszahlungen (transfer_out ohne Bestand)
    darf die Portfolio-Ansicht NICHT mit 500 crashen (insufficient_holdings)."""
    out = _buy(coin="bitcoin", qty=1.0, at="2026-01-01")
    out["kind"] = "transfer_out"
    out["price"] = 0.0
    r = client.post(f"{PREFIX}/portfolio/transactions", json=out, headers=auth_headers)
    assert r.status_code == 200
    # Summary lädt sauber, Position ist geschlossen (quantity 0)
    data = client.get(f"{PREFIX}/portfolio", headers=auth_headers)
    assert data.status_code == 200
    summary = data.json()
    assert summary["totals"]["open_count"] == 0
    # Coin-Detail crasht ebenfalls nicht
    cd = client.get(f"{PREFIX}/portfolio/coin/bitcoin", headers=auth_headers)
    assert cd.status_code == 200
    assert cd.json()["quantity"] == pytest.approx(0.0)


# ---------------------------------------------------------------- Isolation
def test_per_user_isolation(client, auth_headers, other_headers):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(), headers=auth_headers)
    # other sieht nichts
    assert client.get(f"{PREFIX}/portfolio/transactions", headers=other_headers).json() == []
    assert client.get(f"{PREFIX}/portfolio", headers=other_headers).json()["positions"] == []


def test_cannot_delete_foreign_tx(client, auth_headers, other_headers):
    tx_id = client.post(f"{PREFIX}/portfolio/transactions", json=_buy(), headers=auth_headers).json()["id"]
    # other kann fremde tx nicht löschen → 404
    assert client.delete(f"{PREFIX}/portfolio/transactions/{tx_id}", headers=other_headers).status_code == 404
    # testusers tx bleibt
    assert len(client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json()) == 1
