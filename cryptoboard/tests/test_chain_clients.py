"""chain_clients — Parser je Chain gegen gemockte Roh-Responses (kein Netz)."""
from __future__ import annotations

import pytest

from backend import chain_clients as cc


@pytest.mark.asyncio
async def test_base_balance_eth_und_usdc(monkeypatch):
    async def fake_rpc(url, method, params):
        if method == "eth_getBalance":
            return hex(int(0.5 * 1e18))           # 0.5 ETH
        if method == "eth_call":
            return hex(int(998.73 * 1e6))          # 998.73 USDC (6 dec)
        return None
    monkeypatch.setattr(cc, "_rpc", fake_rpc)
    out = await cc.base_balance("0x" + "a" * 40)
    by = {x["symbol"]: x for x in out}
    assert by["ETH"]["amount"] == pytest.approx(0.5)
    assert by["ETH"]["coin_id"] == "ethereum"
    assert by["USDC"]["amount"] == pytest.approx(998.73)
    assert by["USDC"]["coin_id"] == "usd-coin"


@pytest.mark.asyncio
async def test_base_balance_null_wird_ausgelassen(monkeypatch):
    async def fake_rpc(url, method, params):
        return "0x0"
    monkeypatch.setattr(cc, "_rpc", fake_rpc)
    assert await cc.base_balance("0x" + "a" * 40) == []


@pytest.mark.asyncio
async def test_tron_balance(monkeypatch):
    async def fake_get(url):
        return {"tokenBalances": [
            {"tokenAbbr": "trx", "balance": "159351932", "tokenDecimal": 6, "tokenId": "_"},
        ]}
    monkeypatch.setattr(cc, "_get", fake_get)
    out = await cc.tron_balance("T" + "9" * 33)
    assert out == [{"symbol": "TRX", "amount": pytest.approx(159.351932), "coin_id": "tron"}]


@pytest.mark.asyncio
async def test_btc_balance(monkeypatch):
    async def fake_get(url):
        return {"chain_stats": {"funded_txo_sum": 466504, "spent_txo_sum": 0}}
    monkeypatch.setattr(cc, "_get", fake_get)
    out = await cc.btc_balance("bc1q" + "z" * 38)
    assert out[0]["symbol"] == "BTC"
    assert out[0]["amount"] == pytest.approx(0.00466504)


@pytest.mark.asyncio
async def test_btc_balance_leer(monkeypatch):
    async def fake_get(url):
        return {"chain_stats": {"funded_txo_sum": 466504, "spent_txo_sum": 466504}}
    monkeypatch.setattr(cc, "_get", fake_get)
    assert await cc.btc_balance("bc1q" + "z" * 38) == []


@pytest.mark.asyncio
async def test_fetch_balance_fehler_isoliert(monkeypatch):
    async def boom(address):
        raise RuntimeError("explorer down")
    monkeypatch.setattr(cc, "tron_balance", boom)
    # fetch_balance fängt den Fehler → leere Liste, kein Crash
    assert await cc.fetch_balance("tron", "T" + "9" * 33) == []


@pytest.mark.asyncio
async def test_fetch_balance_unbekannte_chain():
    assert await cc.fetch_balance("dogechain", "x") == []
