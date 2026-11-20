"""Gemeinsame buchbar-Regel (onchain_rules): Preview und Commit urteilen gleich.

Fall aus Tills Daten: Swap mit einem nicht auflösbaren Token – die Seite hat einen
abgeleiteten Preis, aber KEINE coin_id. Sie darf weder in counts.buchbar zählen noch
gebucht werden (Commit: coin_id_fehlt).
"""
from __future__ import annotations

import pytest

from backend import addresses_store, alchemy_client as ac, alchemy_key, client as cg
from backend import onchain_resolve as rs, onchain_rules as rules, portfolio_store, price_history
from backend import price_history_store as ps, tron_history as th

PREFIX = "/api/modules/cryptoboard"
URL_ALL = f"{PREFIX}/portfolio/import/onchain/preview_all"
URL_COMMIT = f"{PREFIX}/portfolio/import/onchain/commit"
USER = "testuser"
ADDR = "0x" + "c" * 40
POOL = "0x" + "d" * 40
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
UNK = "0x" + "7" * 40
DAY = "2026-11-18"
TS = f"{DAY}T12:00:00.000Z"
H = "0x" + "5" * 64


def _erc20(frm, to, contract, value, dec, sym):
    return {"hash": H, "blockNum": "0x10", "category": "erc20", "from": frm, "to": to, "asset": sym,
            "metadata": {"blockTimestamp": TS},
            "rawContract": {"address": contract, "value": hex(value), "decimal": hex(dec), "symbol": sym}}


@pytest.fixture
def setup(client, monkeypatch):
    rs.clear_contract_cache()
    transfers = [_erc20(ADDR, POOL, USDC, 100 * 10**6, 6, "USDC"), _erc20(POOL, ADDR, UNK, 7 * 10**18, 18, "UNK")]

    async def fake_fetch(chain, key, address, **kw):
        return {"transfers": transfers, "truncated": False, "before_block": None}

    async def fake_call(chain, key, method, params):
        if method == "eth_getTransactionByHash":
            return {"from": ADDR}
        return {"gasUsed": hex(1), "effectiveGasPrice": hex(1)}

    async def none_contract(platform, address):
        return None

    async def no_fetch(ids, **kw):
        return {}

    async def no_tron(address, **kw):
        return {"transfers": [], "truncated": False, "before_timestamp": None}

    monkeypatch.setattr(ac, "fetch_transfers", fake_fetch)
    monkeypatch.setattr(ac, "call", fake_call)
    monkeypatch.setattr(cg, "contract", none_contract)
    monkeypatch.setattr(price_history, "ensure_coins", no_fetch)
    monkeypatch.setattr(th, "fetch_transfers", no_tron)
    monkeypatch.setattr(alchemy_key, "get_key", lambda user: "k")
    ps.upsert_series("usd-coin", {DAY: 0.9})
    ps.upsert_series("ethereum", {DAY: 2000.0})
    addr_id = addresses_store.add(USER, "base", ADDR, "Base")
    yield
    portfolio_store.clear_all(USER)
    addresses_store.remove(USER, addr_id)
    rs.clear_contract_cache()


def test_eintrag_ohne_coin_id_ist_nicht_buchbar_und_wird_beim_commit_uebersprungen(client, auth_headers, setup):
    data = client.post(URL_ALL, json={}, headers=auth_headers).json()
    tx = {t["hash"]: t for t in data["transactions"]}
    sell, buy = tx[f"base:{H}:sell"], tx[f"base:{H}:buy"]
    # buy-Seite: Preis abgeleitet (100 × 0.9 / 7), aber keine coin_id
    assert buy["coin_id"] is None and buy["price"] is not None
    assert buy["buchbar"] is False and buy["nicht_buchbar_grund"] == "coin_id_fehlt"
    assert sell["buchbar"] is True and sell["nicht_buchbar_grund"] is None
    assert data["counts"]["buchbar"] == 1  # nur die sell-Seite

    r = client.post(URL_COMMIT, json={"transactions": [sell, buy]}, headers=auth_headers).json()
    assert r["imported"] == 1
    assert r["skipped_details"] == [{"hash": buy["hash"], "reason": "coin_id_fehlt"}]


def test_jeder_eintrag_hat_buchbar_true_oder_false(client, auth_headers, setup):
    data = client.post(URL_ALL, json={}, headers=auth_headers).json()
    entries = data["transactions"] + data["ausgaben"] + [e for p in data["pairs"] for e in p["entries"]]
    assert entries and all(isinstance(e["buchbar"], bool) for e in entries)


@pytest.mark.parametrize("override,reason", [
    ({"hash": "base:0xabc:sell"}, "hash_ungueltig"),
    ({"coin_id": None}, "coin_id_fehlt"),
    ({"coin_id": "UNGÜLTIG!"}, "coin_id_fehlt"),
    ({"price": None}, "preis_fehlt"),
    ({"executed_at": None}, "zeit_ungueltig"),
])
def test_skip_reason_gleich_fuer_dict(override, reason):
    e = {"hash": f"base:{H}:sell", "kind": "sell", "coin_id": "usd-coin", "price": "1",
         "executed_at": "2026-11-18T12:00:00Z", **override}
    assert rules.skip_reason(e) == reason


def test_transfer_out_ohne_preis_buchbar_und_duplikat_nicht():
    e = {"hash": f"base:{H}:transfer_out", "kind": "transfer_out", "coin_id": "usd-coin", "price": None,
         "executed_at": "2026-11-18T12:00:00Z"}
    assert rules.skip_reason(e) is None
    assert rules.skip_reason(e, {e["hash"]}) == "duplikat"
