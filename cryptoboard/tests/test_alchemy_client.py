"""alchemy_client — Methoden-Allowlist, Kill-Switch, Paging, Grenzen (kein echter Netzaufruf)."""
from __future__ import annotations

import pytest

from backend import alchemy_client as ac


def test_allowlist_erlaubt_nur_lesende_methoden():
    assert "alchemy_getAssetTransfers" in ac.ALLOWED_METHODS
    assert "eth_getTransactionReceipt" in ac.ALLOWED_METHODS
    assert "eth_blockNumber" in ac.ALLOWED_METHODS
    assert "eth_getTransactionByHash" in ac.ALLOWED_METHODS


@pytest.mark.parametrize("method", [
    "eth_sendRawTransaction", "eth_sendTransaction", "personal_sign", "eth_sign",
])
@pytest.mark.asyncio
async def test_schreibende_methoden_werden_abgelehnt(method, monkeypatch):
    async def boom(*a, **kw):
        raise AssertionError("darf nie das Netz erreichen")
    monkeypatch.setattr(ac, "_rpc", boom)
    with pytest.raises(ac.MethodNotAllowed):
        await ac.call("base", "fake-key", method, [])


@pytest.mark.asyncio
async def test_kill_switch_blockiert_vor_dem_netz(monkeypatch):
    async def boom(*a, **kw):
        raise AssertionError("darf nie das Netz erreichen")
    monkeypatch.setattr(ac, "_rpc", boom)
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", "0")
    with pytest.raises(ac.AlchemyDisabled):
        await ac.call("base", "fake-key", "eth_blockNumber", [])


@pytest.mark.parametrize("value", ["false", "no", "off", "0"])
def test_kill_switch_werte(monkeypatch, value):
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", value)
    assert ac.enabled() is False


def test_kill_switch_default_an(monkeypatch):
    monkeypatch.delenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", raising=False)
    assert ac.enabled() is True


@pytest.mark.asyncio
async def test_erlaubte_methode_geht_durch(monkeypatch):
    calls = []

    async def fake_rpc(url, method, params):
        calls.append((url, method, params))
        return "0x10"
    monkeypatch.setattr(ac, "_rpc", fake_rpc)
    result = await ac.call("base", "fake-key", "eth_blockNumber", [])
    assert result == "0x10"
    assert calls[0][1] == "eth_blockNumber"
    assert "fake-key" in calls[0][0]  # Key steckt im URL-Pfad — bleibt in dieser Schicht, nie im Fehlertext


def test_chain_url_unbekannte_chain():
    with pytest.raises(ac.ChainNotSupported):
        ac.chain_url("solana", "x")


def test_chain_url_bekannte_chains():
    assert ac.chain_url("base", "k").endswith("/v2/k")
    assert "base-mainnet.g.alchemy.com" in ac.chain_url("base", "k")
    assert "eth-mainnet.g.alchemy.com" in ac.chain_url("ethereum", "k")


# ---------------------------------------------------------------- fetch_transfers: Paging


def _transfer(hash_, ts, block="0x1"):
    return {"hash": hash_, "blockNum": block, "metadata": {"blockTimestamp": ts},
            "rawContract": {"value": "0x1", "decimal": "0x12"}, "from": "0xaa", "to": "0xbb"}


@pytest.mark.asyncio
async def test_fetch_transfers_folgt_pagekey(monkeypatch):
    pages = {
        None: {"transfers": [_transfer("0x1", "2026-01-01T00:00:00Z")], "pageKey": "p2"},
        "p2": {"transfers": [_transfer("0x2", "2026-01-02T00:00:00Z")], "pageKey": None},
    }

    async def fake_call(chain, key, method, params):
        page_key = params[0].get("pageKey")
        return pages[page_key]
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa")
    hashes = {t["hash"] for t in out["transfers"]}
    assert hashes == {"0x1", "0x2"}
    assert out["truncated"] is False


@pytest.mark.asyncio
async def test_fetch_transfers_grenze_1000_transaktionen(monkeypatch):
    # 3 Transfers, Grenze 2 → der dritte triggert truncated
    txs = [_transfer(f"0x{i}", "2026-01-01T00:00:00Z", block=f"0x{i}") for i in range(3)]

    async def fake_call(chain, key, method, params):
        return {"transfers": txs, "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_transactions=2)
    assert out["truncated"] is True
    assert out["before_block"] is not None
    assert len({t["hash"] for t in out["transfers"]}) <= 2


@pytest.mark.asyncio
async def test_fetch_transfers_grenze_2_jahre(monkeypatch):
    alt = _transfer("0xold", "2020-01-01T00:00:00Z")  # älter als 2 Jahre
    neu = _transfer("0xneu", "2026-11-01T00:00:00Z")

    async def fake_call(chain, key, method, params):
        return {"transfers": [neu, alt], "pageKey": None}
    monkeypatch.setattr(ac, "call", fake_call)
    out = await ac.fetch_transfers("base", "fake-key", "0xaa", max_age_years=2)
    hashes = {t["hash"] for t in out["transfers"]}
    assert "0xneu" in hashes
    assert "0xold" not in hashes
    assert out["truncated"] is True


@pytest.mark.asyncio
async def test_fetch_transfers_disabled(monkeypatch):
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", "0")
    with pytest.raises(ac.AlchemyDisabled):
        await ac.fetch_transfers("base", "fake-key", "0xaa")


# ---------------------------------------------------------------- Fehlerklassen: kein Key im Text


@pytest.mark.asyncio
async def test_http_fehler_enthaelt_nie_die_url(monkeypatch):
    import httpx

    class FakeResponse:
        status_code = 401
        text = "Unauthorized"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("boom", request=None, response=self)

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr(ac.httpx, "AsyncClient", lambda timeout: FakeClient())
    with pytest.raises(ac.AlchemyHttpError) as exc_info:
        await ac._rpc("https://base-mainnet.g.alchemy.com/v2/geheimer-key-123", "eth_blockNumber", [])
    assert "geheimer-key-123" not in str(exc_info.value)
    assert exc_info.value.status_code == 401
    assert "geheimer-key-123" not in exc_info.value.body
