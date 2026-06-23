"""C8 — CSV-Import: preview (Mapping+Auflösung+Dedup) & commit (schreiben+Dedup).

client.search gemockt — kein echter Netz-Traffic.
"""
from __future__ import annotations

import pytest

from backend import client as cg

PREFIX = "/api/modules/cryptoboard"

_CSV = (
    "Date,Type,Asset,Amount,Price,Fee\n"
    "2026-01-01,Buy,BTC,0.5,40000,10\n"
    "2026-02-01,Sell,BTC,0.2,50000,5\n"
    "2026-03-01,Buy,ETH,3,3000,2\n"
)


@pytest.fixture(autouse=True)
def mock_search(monkeypatch):
    table = {
        "BTC": [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "market_cap_rank": 1}],
        "ETH": [{"id": "ethereum", "symbol": "ETH", "name": "Ethereum", "market_cap_rank": 2}],
        "XYZ": [],  # unauflösbar
    }

    async def fake_search(q):
        return table.get(q.upper(), [])

    monkeypatch.setattr(cg, "search", fake_search)


# ---------------------------------------------------------------- preview
def test_preview_braucht_auth(client):
    assert client.post(f"{PREFIX}/portfolio/import/preview", json={"csv": _CSV}).status_code == 401


def test_preview_mapping_und_aufloesung(client, auth_headers):
    r = client.post(f"{PREFIX}/portfolio/import/preview", json={"csv": _CSV}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["mapping"]["symbol"] == "Asset"
    assert data["mapping"]["quantity"] == "Amount"
    assert len(data["transactions"]) == 3
    btc = next(t for t in data["transactions"] if t["symbol"] == "BTC")
    assert btc["coin_id"] == "bitcoin"
    assert btc["resolved"] is True
    assert btc["duplicate"] is False
    assert data["unresolved_symbols"] == []


def test_preview_unaufloesbares_symbol(client, auth_headers):
    csv = "Date,Type,Asset,Amount\n2026-01-01,Buy,XYZ,1\n"
    r = client.post(f"{PREFIX}/portfolio/import/preview", json={"csv": csv}, headers=auth_headers)
    data = r.json()
    assert data["transactions"][0]["resolved"] is False
    assert data["unresolved_symbols"] == ["XYZ"]


def test_preview_fehlerhafte_zeilen(client, auth_headers):
    csv = "Date,Type,Asset,Amount\n2026-01-01,Buy,BTC,1\n,,,\n2026-02-01,Buy,,abc\n"
    r = client.post(f"{PREFIX}/portfolio/import/preview", json={"csv": csv}, headers=auth_headers)
    data = r.json()
    assert len(data["transactions"]) == 1
    assert len(data["errors"]) >= 1


def test_preview_leeres_csv_400(client, auth_headers):
    r = client.post(f"{PREFIX}/portfolio/import/preview", json={"csv": "   "}, headers=auth_headers)
    assert r.status_code == 422 or r.status_code == 400


# ---------------------------------------------------------------- commit
def _preview(client, auth_headers, csv=_CSV):
    return client.post(f"{PREFIX}/portfolio/import/preview", json={"csv": csv}, headers=auth_headers).json()


def _commit_payload(prev: dict) -> dict:
    return {"transactions": [
        {
            "coin_id": t["coin_id"], "symbol": t["symbol"], "name": t.get("coin_name") or "",
            "kind": t["kind"], "quantity": t["quantity"], "price": t["price"],
            "fee": t["fee"], "executed_at": t["executed_at"], "hash": t["hash"],
        }
        for t in prev["transactions"]
    ]}


def test_commit_schreibt_transaktionen(client, auth_headers):
    prev = _preview(client, auth_headers)
    r = client.post(f"{PREFIX}/portfolio/import/commit", json=_commit_payload(prev), headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["imported"] == 3

    # Transaktionen sind jetzt im Ledger
    txs = client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json()
    assert len(txs) == 3


def test_commit_dedup_beim_zweiten_import(client, auth_headers):
    prev = _preview(client, auth_headers)
    payload = _commit_payload(prev)
    first = client.post(f"{PREFIX}/portfolio/import/commit", json=payload, headers=auth_headers).json()
    assert first["imported"] == 3

    # Zweiter Commit derselben Daten → alles übersprungen
    second = client.post(f"{PREFIX}/portfolio/import/commit", json=payload, headers=auth_headers).json()
    assert second["imported"] == 0
    assert second["skipped"] == 3
    # Ledger weiterhin nur 3 Einträge
    assert len(client.get(f"{PREFIX}/portfolio/transactions", headers=auth_headers).json()) == 3


def test_commit_zweiter_preview_markiert_duplikate(client, auth_headers):
    prev = _preview(client, auth_headers)
    client.post(f"{PREFIX}/portfolio/import/commit", json=_commit_payload(prev), headers=auth_headers)
    # Erneuter Preview erkennt die bereits importierten Zeilen
    prev2 = _preview(client, auth_headers)
    assert prev2["duplicate_count"] == 3
    assert all(t["duplicate"] for t in prev2["transactions"])


def test_commit_ungueltige_coin_id_skipped(client, auth_headers):
    payload = {"transactions": [
        {"coin_id": "BAD ID!", "symbol": "X", "name": "", "kind": "buy",
         "quantity": 1.0, "price": 1.0, "fee": 0.0, "executed_at": "2026-01-01", "hash": "abc"},
    ]}
    r = client.post(f"{PREFIX}/portfolio/import/commit", json=payload, headers=auth_headers)
    assert r.json()["imported"] == 0
    assert r.json()["skipped"] == 1


def test_commit_leer(client, auth_headers):
    r = client.post(f"{PREFIX}/portfolio/import/commit", json={"transactions": []}, headers=auth_headers)
    assert r.json()["imported"] == 0
