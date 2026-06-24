"""C10 — Wallets: Adress-Validierung (rein), CRUD, Bestands-Aggregation (gemockt)."""
from __future__ import annotations

import pytest

from backend import address_validators as av
from backend import chain_clients, client as cg

PREFIX = "/api/modules/cryptoboard"

# Synthetische, formatgültige Adressen (nicht Tills echte)
ADDR = {
    "base": "0x" + "a" * 40,
    "tron": "T" + "9" * 33,
    "bitcoin": "bc1q" + "z" * 38,
}


# ---------------------------------------------------------------- Validatoren
def test_valid_chain():
    assert av.is_valid_chain("base") and av.is_valid_chain("tron") and av.is_valid_chain("bitcoin")
    assert av.is_valid_chain("ethereum")
    assert not av.is_valid_chain("solana")
    assert not av.is_valid_chain("")


@pytest.mark.parametrize("chain,addr,ok", [
    ("base", "0x" + "A" * 40, True),
    ("base", "0x" + "g" * 40, False),       # kein Hex
    ("base", "0x" + "a" * 39, False),       # zu kurz
    ("tron", "T" + "9" * 33, True),
    ("tron", "X" + "9" * 33, False),        # falscher Prefix
    ("bitcoin", "bc1q" + "z" * 38, True),
    ("bitcoin", "1" + "A" * 30, True),      # legacy
    ("bitcoin", "xyz", False),
])
def test_address_format(chain, addr, ok):
    assert av.is_valid_address(chain, addr) is ok


def test_address_wrong_chain_rejected():
    # EVM-Adresse als tron → ungültig
    assert not av.is_valid_address("tron", "0x" + "a" * 40)


# ---------------------------------------------------------------- CRUD
def test_wallets_braucht_auth(client):
    assert client.get(f"{PREFIX}/wallets").status_code == 401


def test_add_list_remove(client, auth_headers):
    assert client.get(f"{PREFIX}/wallets", headers=auth_headers).json() == []
    r = client.post(f"{PREFIX}/wallets", json={"chain": "tron", "address": ADDR["tron"], "label": "Haupt"}, headers=auth_headers)
    assert r.status_code == 200
    aid = r.json()["id"]
    items = client.get(f"{PREFIX}/wallets", headers=auth_headers).json()
    assert len(items) == 1 and items[0]["chain"] == "tron" and items[0]["label"] == "Haupt"
    assert client.delete(f"{PREFIX}/wallets/{aid}", headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/wallets", headers=auth_headers).json() == []


def test_mehrere_adressen_pro_chain(client, auth_headers):
    client.post(f"{PREFIX}/wallets", json={"chain": "base", "address": "0x" + "a" * 40}, headers=auth_headers)
    client.post(f"{PREFIX}/wallets", json={"chain": "base", "address": "0x" + "b" * 40}, headers=auth_headers)
    assert len(client.get(f"{PREFIX}/wallets", headers=auth_headers).json()) == 2


def test_invalid_chain_400(client, auth_headers):
    r = client.post(f"{PREFIX}/wallets", json={"chain": "solana", "address": "x"}, headers=auth_headers)
    assert r.status_code == 400


def test_invalid_address_400(client, auth_headers):
    r = client.post(f"{PREFIX}/wallets", json={"chain": "base", "address": "nonsense"}, headers=auth_headers)
    assert r.status_code == 400


def test_delete_unknown_404(client, auth_headers):
    assert client.delete(f"{PREFIX}/wallets/9999", headers=auth_headers).status_code == 404


@pytest.fixture
def other_headers(client):
    r = client.post("/api/auth/login", json={"username": "other", "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_per_user_isolation(client, auth_headers, other_headers):
    aid = client.post(f"{PREFIX}/wallets", json={"chain": "tron", "address": ADDR["tron"]}, headers=auth_headers).json()["id"]
    assert client.get(f"{PREFIX}/wallets", headers=other_headers).json() == []
    assert client.delete(f"{PREFIX}/wallets/{aid}", headers=other_headers).status_code == 404


# ---------------------------------------------------------------- Balances (gemockt)
def test_balances_aggregiert_eur(client, auth_headers, monkeypatch):
    async def fake_fetch(chain, address):
        return {"tron": [{"symbol": "TRX", "amount": 1000.0, "coin_id": "tron"}],
                "base": [{"symbol": "USDC", "amount": 500.0, "coin_id": "usd-coin"}]}.get(chain, [])

    async def fake_markets(vs, *, ids=None, top=None):
        p = {"tron": 0.20, "usd-coin": 0.90}
        return [{"id": i, "price": p.get(i, 0)} for i in (ids or [])]

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    monkeypatch.setattr(cg, "markets", fake_markets)

    client.post(f"{PREFIX}/wallets", json={"chain": "tron", "address": ADDR["tron"]}, headers=auth_headers)
    client.post(f"{PREFIX}/wallets", json={"chain": "base", "address": ADDR["base"]}, headers=auth_headers)

    data = client.get(f"{PREFIX}/wallets/balances", headers=auth_headers).json()
    assert data["currency"] == "EUR"
    # TRX: 1000*0.20=200, USDC: 500*0.90=450 → total 650
    assert data["total"] == pytest.approx(650.0)
    assert len(data["addresses"]) == 2


def test_balances_aggregiert_token_ueber_wallets(client, auth_headers, monkeypatch):
    # Gleicher Token (TRX) auf zwei Wallets → eine aggregierte Zeile mit 2 wallets
    async def fake_fetch(chain, address):
        return [{"symbol": "TRX", "amount": 100.0, "coin_id": "tron"}]

    async def fake_markets(vs, *, ids=None, top=None):
        return [{"id": "tron", "price": 0.20}]

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    monkeypatch.setattr(cg, "markets", fake_markets)
    client.post(f"{PREFIX}/wallets", json={"chain": "tron", "address": "T" + "9" * 33, "label": "A"}, headers=auth_headers)
    client.post(f"{PREFIX}/wallets", json={"chain": "tron", "address": "T" + "8" * 33, "label": "B"}, headers=auth_headers)

    data = client.get(f"{PREFIX}/wallets/balances", headers=auth_headers).json()
    trx = [t for t in data["tokens"] if t["symbol"] == "TRX"][0]
    assert trx["amount"] == pytest.approx(200.0)        # 100 + 100 aggregiert
    assert trx["value"] == pytest.approx(40.0)          # 200 * 0.20
    assert len(trx["wallets"]) == 2                       # auf beiden Wallets sichtbar


def test_balances_wert_via_price_trx(client, auth_headers, monkeypatch):
    # Obskurer Token ohne coin_id, aber mit Tronscan price_trx → Wert berechenbar
    async def fake_fetch(chain, address):
        return [
            {"symbol": "TRX", "amount": 1000.0, "coin_id": "tron"},
            {"symbol": "OBSCURE", "amount": 50.0, "coin_id": None, "price_trx": 2.0, "verified": True, "token_id": "1009"},
            {"symbol": "SPAM", "amount": 8888.0, "coin_id": None, "price_trx": None, "verified": False, "token_id": "1005"},
        ]

    async def fake_markets(vs, *, ids=None, top=None):
        return [{"id": "tron", "price": 0.20}]

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    monkeypatch.setattr(cg, "markets", fake_markets)
    client.post(f"{PREFIX}/wallets", json={"chain": "tron", "address": ADDR["tron"]}, headers=auth_headers)

    data = client.get(f"{PREFIX}/wallets/balances", headers=auth_headers).json()
    by = {t["symbol"]: t for t in data["tokens"]}
    # OBSCURE: 50 * 2.0 (price_trx) * 0.20 (trx_eur) = 20.0
    assert by["OBSCURE"]["value"] == pytest.approx(20.0) and by["OBSCURE"]["value_known"]
    # SPAM bleibt sichtbar, aber Wert unbekannt
    assert by["SPAM"]["value_known"] is False
    # total = TRX(200) + OBSCURE(20) = 220; SPAM zählt nicht mit
    assert data["total"] == pytest.approx(220.0)


def test_balances_kaputte_chain_bricht_nicht(client, auth_headers, monkeypatch):
    # fetch_balance liefert für eine Adresse [] (Fehler isoliert) → Ansicht lädt trotzdem
    async def fake_fetch(chain, address):
        return []

    async def fake_markets(vs, *, ids=None, top=None):
        return []

    monkeypatch.setattr(chain_clients, "fetch_balance", fake_fetch)
    monkeypatch.setattr(cg, "markets", fake_markets)
    client.post(f"{PREFIX}/wallets", json={"chain": "bitcoin", "address": ADDR["bitcoin"]}, headers=auth_headers)
    data = client.get(f"{PREFIX}/wallets/balances", headers=auth_headers).json()
    assert data["total"] == 0.0
    assert len(data["addresses"]) == 1
