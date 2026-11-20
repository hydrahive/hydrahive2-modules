"""On-Chain-Import: Preview/Commit über die Routen, ganzer Weg gemockt.

fetch_transfers, Receipt/TxByHash (alchemy_client.call), CoinGecko-Kontraktsuche
und Kursabruf sind ersetzt — kein Netz. Kurse liegen direkt im price_history_store.
"""
from __future__ import annotations

import logging

import pytest

from backend import addresses_store, alchemy_client as ac, alchemy_key, client as cg
from backend import onchain_resolve as rs, portfolio_store, price_history, price_history_store as ps

PREFIX = "/api/modules/cryptoboard"
URL_P = f"{PREFIX}/portfolio/import/onchain/preview"
URL_C = f"{PREFIX}/portfolio/import/onchain/commit"
USER = "testuser"
KEY = "GEHEIMKEY-onchain-route-1234567890"
ADDR = "0x" + "a" * 40
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
DAY = "2026-06-15"
TS = f"{DAY}T12:00:00.000Z"
H1, H2, H3, H4 = ("0x" + c * 64 for c in "1234")


def _erc20(h, frm, to, contract, value, dec, sym):
    return {"hash": h, "blockNum": "0x10", "category": "erc20", "from": frm, "to": to, "asset": sym,
            "metadata": {"blockTimestamp": TS},
            "rawContract": {"address": contract, "value": hex(value), "decimal": hex(dec), "symbol": sym}}


def _eth(h, frm, to, value, category="external"):
    return {"hash": h, "blockNum": "0x10", "category": category, "from": frm, "to": to, "asset": "ETH",
            "metadata": {"blockTimestamp": TS}, "rawContract": {"address": None, "value": hex(value), "decimal": "0x12"}}


TRANSFERS = [
    # H1: Adresse zahlt 1000 USDC, bekommt 0.5 ETH (Absender → Gas)
    _erc20(H1, ADDR, "0xpool", USDC, 1000 * 10**6, 6, "USDC"),
    _eth(H1, "0xpool", ADDR, 5 * 10**17, "internal"),
    # H2: nur rein (Airdrop) → unklar
    _erc20(H2, "0xdrop", ADDR, USDC, 5 * 10**6, 6, "USDC"),
    # H3: Wrap ETH → WETH
    _eth(H3, ADDR, "0x4200000000000000000000000000000000000006", 10**18),
    _erc20(H3, "0x4200000000000000000000000000000000000006", ADDR,
           "0x4200000000000000000000000000000000000006", 10**18, 18, "WETH"),
    # H4: Fremder hat getriggert, Adresse ist nur Empfängerin beider Seiten? → Swap ohne Absender:
    # Adresse gibt UNKNOWN-Token (Kontrakt unbekannt, keine Suche), bekommt USDC; Tx-from ist fremd
    _erc20(H4, ADDR, "0xpool", "0x" + "b" * 40, 7 * 10**18, 18, "UNK"),
    _erc20(H4, "0xpool", ADDR, USDC, 70 * 10**6, 6, "USDC"),
]


@pytest.fixture
def setup(client, monkeypatch):
    rs.clear_contract_cache()
    fetch_calls = []

    async def fake_fetch(chain, key, address, *, to_block="latest", **kw):
        fetch_calls.append({"chain": chain, "key": key, "to_block": to_block})
        return {"transfers": TRANSFERS, "truncated": True, "before_block": "0x10"}

    async def fake_call(chain, key, method, params):
        if method == "eth_getTransactionReceipt":
            # 100000 gas × 1 gwei + l1Fee 0.0001 ETH = 0.0002 ETH
            return {"gasUsed": hex(100000), "effectiveGasPrice": hex(10**9), "l1Fee": hex(10**14)}
        if method == "eth_getTransactionByHash":
            return {"from": ADDR if params[0] == H1 else "0x" + "f" * 40}
        raise AssertionError(method)

    async def fake_contract(platform, address):
        return None  # unbekannter Token bleibt unresolved

    async def no_fetch(ids, **kw):
        return {}

    monkeypatch.setattr(ac, "fetch_transfers", fake_fetch)
    monkeypatch.setattr(ac, "call", fake_call)
    monkeypatch.setattr(cg, "contract", fake_contract)
    monkeypatch.setattr(price_history, "ensure_coins", no_fetch)
    monkeypatch.setattr(alchemy_key, "get_key", lambda user: KEY)
    ps.upsert_series("usd-coin", {DAY: 0.9})
    ps.upsert_series("ethereum", {DAY: 2000.0})
    addr_id = addresses_store.add(USER, "base", ADDR, "Test")
    yield {"addr_id": addr_id, "fetch_calls": fetch_calls}
    portfolio_store.clear_all(USER)
    addresses_store.remove(USER, addr_id)
    rs.clear_contract_cache()


def _preview(client, auth_headers, setup, **extra):
    r = client.post(URL_P, json={"address_id": setup["addr_id"], **extra}, headers=auth_headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_preview_swap_eintraege_preise_gas(client, auth_headers, setup):
    data = _preview(client, auth_headers, setup)
    tx = {t["hash"]: t for t in data["transactions"]}
    sell = tx[f"base:{H1}:sell"]
    buy = tx[f"base:{H1}:buy"]
    assert (sell["coin_id"], sell["kind"], sell["quantity"], sell["price"]) == ("usd-coin", "sell", "1000", "0.9")
    # Wert 900 EUR (Stable-Seite) / 0.5 ETH = 1800 EUR je ETH
    assert (buy["coin_id"], buy["quantity"], buy["price"]) == ("ethereum", "0.5", "1800")
    # Gas: 0.0002 ETH × 2000 = 0.4 EUR, nur auf sell
    assert sell["fee"] == "0.4" and buy["fee"] == "0"
    assert sell["executed_at"] == f"{DAY}T12:00:00Z"
    assert not sell["preis_fehlt"] and not sell["gebuehr_fehlt"] and sell["resolved"]


def test_preview_gas_nur_als_absender(client, auth_headers, setup):
    data = _preview(client, auth_headers, setup)
    sell = {t["hash"]: t for t in data["transactions"]}[f"base:{H4}:sell"]
    assert sell["fee"] == "0" and not sell["gebuehr_fehlt"]


def test_preview_unresolved_und_abgeleiteter_preis(client, auth_headers, setup):
    tx = {t["hash"]: t for t in _preview(client, auth_headers, setup)["transactions"]}
    sell = tx[f"base:{H4}:sell"]
    assert sell["coin_id"] is None and sell["resolved"] is False
    assert sell["price"] == "9"  # 70 USDC × 0.9 / 7 UNK
    assert tx[f"base:{H4}:buy"]["price"] == "0.9"


def test_preview_unklar_wraps_truncated(client, auth_headers, setup):
    data = _preview(client, auth_headers, setup, to_block="0x99")
    assert setup["fetch_calls"][-1]["to_block"] == "0x99"
    assert data["truncated"] is True and data["before_block"] == "0x10"
    assert [u["hash"] for u in data["unklar"]] == [H2]
    assert data["unklar"][0]["tokens"][0] == {
        "symbol": "USDC", "contract": USDC, "category": "erc20", "direction": "rein", "amount": "5"}
    assert [w["hash"] for w in data["wraps"]] == [H3]
    assert data["counts"]["swaps"] == 2 and data["counts"]["transactions"] == 4


def test_preview_preis_fehlt(client, auth_headers, setup):
    from hydrahive.db import db
    with db() as c:
        c.execute("DELETE FROM module_cryptoboard_price_history WHERE day = ?", (DAY,))
    data = _preview(client, auth_headers, setup)
    sell = {t["hash"]: t for t in data["transactions"]}[f"base:{H1}:sell"]
    assert sell["price"] is None and sell["preis_fehlt"] is True
    assert sell["fee"] is None and sell["gebuehr_fehlt"] is True  # kein ETH-Kurs am Tag


def test_commit_dedup_zweimal(client, auth_headers, setup):
    entries = [t for t in _preview(client, auth_headers, setup)["transactions"] if t["coin_id"]]
    r1 = client.post(URL_C, json={"transactions": entries}, headers=auth_headers).json()
    assert r1["imported"] == 3 and r1["skipped"] == 0
    rows = portfolio_store.list_for(USER)
    assert {r["note"] for r in rows} == {"On-Chain-Import"}
    assert {r["import_hash"] for r in rows} == {e["hash"] for e in entries}
    eth = [r for r in rows if r["coin_id"] == "ethereum"][0]
    assert eth["quantity"] == 0.5 and eth["price"] == 1800.0
    r2 = client.post(URL_C, json={"transactions": entries}, headers=auth_headers).json()
    assert r2["imported"] == 0 and r2["skipped"] == 3
    assert {d["reason"] for d in r2["skipped_details"]} == {"duplikat"}
    assert len(portfolio_store.list_for(USER)) == 3
    # Preview markiert nun alles Gebuchte als duplicate
    again = {t["hash"]: t for t in _preview(client, auth_headers, setup)["transactions"]}
    assert all(again[e["hash"]]["duplicate"] for e in entries)


def test_commit_dedup_innerhalb_eines_requests(client, auth_headers, setup):
    e = [t for t in _preview(client, auth_headers, setup)["transactions"] if t["hash"] == f"base:{H1}:buy"]
    r = client.post(URL_C, json={"transactions": e + e}, headers=auth_headers).json()
    assert r["imported"] == 1 and r["skipped"] == 1


def test_commit_ohne_preis_oder_coin_id_skipped(client, auth_headers, setup):
    tx = {t["hash"]: t for t in _preview(client, auth_headers, setup)["transactions"]}
    no_price = dict(tx[f"base:{H1}:sell"], price=None)
    no_coin = tx[f"base:{H4}:sell"]  # coin_id None
    r = client.post(URL_C, json={"transactions": [no_price, no_coin]}, headers=auth_headers).json()
    assert r["imported"] == 0
    assert sorted(d["reason"] for d in r["skipped_details"]) == ["coin_id_fehlt", "preis_fehlt"]
    assert portfolio_store.list_for(USER) == []


def test_commit_fee_none_wird_0(client, auth_headers, setup):
    e = dict({t["hash"]: t for t in _preview(client, auth_headers, setup)["transactions"]}[f"base:{H1}:sell"],
             fee=None)
    assert client.post(URL_C, json={"transactions": [e]}, headers=auth_headers).json()["imported"] == 1
    assert portfolio_store.list_for(USER)[0]["fee"] == 0


def test_commit_fremder_hash_abgelehnt(client, auth_headers, setup):
    e = dict({t["hash"]: t for t in _preview(client, auth_headers, setup)["transactions"]}[f"base:{H1}:sell"],
             hash="CSV-irgendwas")
    r = client.post(URL_C, json={"transactions": [e]}, headers=auth_headers).json()
    assert r["imported"] == 0 and r["skipped_details"][0]["reason"] == "hash_ungueltig"


def test_preview_fremde_adresse_404(client, auth_headers, setup):
    other = addresses_store.add("someoneelse", "base", ADDR, "fremd")
    try:
        r = client.post(URL_P, json={"address_id": other}, headers=auth_headers)
        assert r.status_code == 404
        assert "address_not_found" in r.text
    finally:
        addresses_store.remove("someoneelse", other)


def test_preview_chain_nicht_unterstuetzt(client, auth_headers, setup):
    btc = addresses_store.add(USER, "bitcoin", "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "btc")
    r = client.post(URL_P, json={"address_id": btc}, headers=auth_headers)
    addresses_store.remove(USER, btc)
    assert r.status_code == 400 and "onchain_chain_not_supported" in r.text


def test_preview_key_fehlt(client, auth_headers, setup, monkeypatch):
    monkeypatch.setattr(alchemy_key, "get_key", lambda user: None)
    r = client.post(URL_P, json={"address_id": setup["addr_id"]}, headers=auth_headers)
    assert r.status_code == 409 and "alchemy_key_missing" in r.text


def test_preview_kill_switch(client, auth_headers, setup, monkeypatch):
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", "0")
    r = client.post(URL_P, json={"address_id": setup["addr_id"]}, headers=auth_headers)
    assert r.status_code == 503 and "cryptoboard_onchain_disabled" in r.text


@pytest.mark.parametrize("exc,code,status", [
    (ac.AlchemyHttpError(401, "Must be authenticated!"), "alchemy_key_invalid", 401),
    (ac.AlchemyHttpError(403, "Base is not enabled for this app"), "alchemy_base_not_enabled", 403),
    (ac.AlchemyHttpError(500, "oops"), "alchemy_fetch_failed", 502),
    (ac.AlchemyNetworkError(), "alchemy_network_error", 502),
])
def test_preview_alchemy_fehler_als_code_ohne_key(client, auth_headers, setup, monkeypatch, caplog,
                                                   exc, code, status):
    async def failing(*a, **kw):
        raise exc

    monkeypatch.setattr(ac, "fetch_transfers", failing)
    caplog.set_level(logging.DEBUG)
    r = client.post(URL_P, json={"address_id": setup["addr_id"]}, headers=auth_headers)
    assert r.status_code == status and code in r.text
    assert KEY not in r.text and KEY not in caplog.text


def test_preview_antwort_enthaelt_nie_den_key(client, auth_headers, setup, caplog):
    caplog.set_level(logging.DEBUG)
    r = client.post(URL_P, json={"address_id": setup["addr_id"]}, headers=auth_headers)
    assert r.status_code == 200
    assert KEY not in r.text and KEY not in caplog.text


def test_preview_braucht_auth(client, setup):
    assert client.post(URL_P, json={"address_id": setup["addr_id"]}).status_code == 401
    assert client.post(URL_C, json={"transactions": []}).status_code == 401
