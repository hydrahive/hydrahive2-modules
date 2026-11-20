"""tron_history — Paging, Grenzen (1000 Tx / 2 Jahre), Filter (confirmed/SUCCESS/contractType 1 bzw. 31 mit callValue)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest

from backend import tron_history as th

ADDR = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
NOW = datetime.now(timezone.utc)


def _row(hash_, ts, owner, to, amount, *, contract_type=1, confirmed=True, ret="SUCCESS", fee=0):
    return {
        "hash": hash_, "timestamp": int(ts.timestamp() * 1000),
        "ownerAddress": owner, "toAddress": to, "contractType": contract_type,
        "confirmed": confirmed, "contractRet": ret, "amount": str(amount),
        "cost": {"fee": fee},
    }


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    monkeypatch.delenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", raising=False)


def test_sun_to_trx_exakt():
    assert th.sun_to_trx(8_000_000_000) == Decimal("8000")
    assert th.sun_to_trx(1) == Decimal("1") / Decimal(10**6)


@pytest.mark.asyncio
async def test_fetch_transfers_grundfall(monkeypatch):
    rows = [_row("a1", NOW, ADDR, "Tto", 8_000_000_000, fee=1_100_000)]

    async def fake_get(params):
        assert params["address"] == ADDR
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert len(out["transfers"]) == 1
    t = out["transfers"][0]
    assert t["hash"] == "a1"
    assert t["amount_sun"] == 8_000_000_000
    assert t["fee_sun"] == 1_100_000
    assert t["from"] == ADDR
    assert out["truncated"] is False


@pytest.mark.asyncio
async def test_filtert_contract_type_ungleich_1(monkeypatch):
    rows = [_row("a1", NOW, ADDR, "Tto", 100, contract_type=31)]

    async def fake_get(params):
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert out["transfers"] == []


@pytest.mark.asyncio
async def test_filtert_nicht_confirmed(monkeypatch):
    rows = [_row("a1", NOW, ADDR, "Tto", 100, confirmed=False)]

    async def fake_get(params):
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert out["transfers"] == []


@pytest.mark.asyncio
async def test_filtert_failed(monkeypatch):
    rows = [_row("a1", NOW, ADDR, "Tto", 100, ret="FAILED")]

    async def fake_get(params):
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert out["transfers"] == []


@pytest.mark.asyncio
async def test_paging_mehrere_seiten(monkeypatch):
    page0 = [_row(f"p0-{i}", NOW - timedelta(minutes=i), ADDR, "Tto", 1) for i in range(50)]
    page1 = [_row(f"p1-{i}", NOW - timedelta(minutes=50 + i), ADDR, "Tto", 1) for i in range(10)]
    calls = []

    async def fake_get(params):
        calls.append(params["start"])
        if params["start"] == 0:
            return {"total": 60, "data": page0}
        return {"total": 60, "data": page1}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert calls == [0, 50]
    assert len(out["transfers"]) == 60
    assert out["truncated"] is False


@pytest.mark.asyncio
async def test_grenze_1000_transaktionen(monkeypatch):
    rows = [_row(f"h{i}", NOW - timedelta(minutes=i), ADDR, "Tto", 1) for i in range(5)]

    async def fake_get(params):
        return {"total": 5, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR, max_transactions=3)
    assert len(out["transfers"]) == 3
    assert out["truncated"] is True
    assert out["before_timestamp"] is not None


@pytest.mark.asyncio
async def test_grenze_2_jahre(monkeypatch):
    neu = _row("neu", NOW, ADDR, "Tto", 1)
    alt = _row("alt", NOW - timedelta(days=800), ADDR, "Tto", 1)

    async def fake_get(params):
        return {"total": 2, "data": [neu, alt]}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR, max_age_years=2)
    hashes = {t["hash"] for t in out["transfers"]}
    assert hashes == {"neu"}
    assert out["truncated"] is True


@pytest.mark.asyncio
async def test_kill_switch(monkeypatch):
    monkeypatch.setenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED", "0")
    with pytest.raises(th.TronDisabled):
        await th.fetch_transfers(ADDR)


@pytest.mark.asyncio
async def test_netzfehler_wird_zu_festem_code(monkeypatch):
    async def boom(params):
        raise httpx.ConnectError("boom")
    monkeypatch.setattr(th, "_get", boom)
    with pytest.raises(th.TronNetworkError):
        await th.fetch_transfers(ADDR)


@pytest.mark.asyncio
async def test_http_fehler_wird_zu_festem_code_ohne_rohtext(monkeypatch):
    class FakeResp:
        status_code = 500
        text = "geheimer rohtext den wir nie zeigen"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("boom", request=None, response=self)

    async def fake_get_http(self, url, params=None):
        return FakeResp()

    async def boom(params):
        resp = FakeResp()
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise th.TronFetchFailed(exc.response.status_code) from None
    monkeypatch.setattr(th, "_get", boom)
    with pytest.raises(th.TronFetchFailed) as exc_info:
        await th.fetch_transfers(ADDR)
    assert "geheimer rohtext" not in str(exc_info.value)
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------- contractType 31 (TriggerSmartContract) mit TRX-callValue
SWAP_CONTRACT = "TJ4KeiGTvTX4wRUgLARiwr8rGLaurmVkdZ"


def _trigger_row(hash_, ts, owner, call_value, *, method="swapEth", amount=None, fee=345_000):
    """Rohformat wie tronscan /api/transaction bei Tills swapEth-Aufruf (03.11. 14:54)."""
    data: dict = {"owner_address": owner, "contract_address": SWAP_CONTRACT}
    if call_value is not None:
        data["call_value"] = call_value
    return {
        "hash": hash_, "timestamp": int(ts.timestamp() * 1000),
        "ownerAddress": owner, "toAddress": SWAP_CONTRACT, "contractType": 31,
        "confirmed": True, "contractRet": "SUCCESS",
        "amount": str(call_value if amount is None else amount),
        "contractData": data, "trigger_info": {"methodName": method},
        "cost": {"fee": fee},
    }


@pytest.mark.asyncio
async def test_trigger_contract_mit_call_value_ist_trx_abgang(monkeypatch):
    rows = [_trigger_row("s1", NOW, ADDR, 2_000_000_000)]

    async def fake_get(params):
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert len(out["transfers"]) == 1
    t = out["transfers"][0]
    assert t["amount_sun"] == 2_000_000_000
    assert th.sun_to_trx(t["amount_sun"]) == Decimal("2000")
    assert t["from"] == ADDR
    assert t["to"] == SWAP_CONTRACT
    assert t["fee_sun"] == 345_000


@pytest.mark.asyncio
async def test_trigger_contract_menge_kommt_aus_call_value(monkeypatch):
    # Top-Level-amount weicht ab → maßgeblich ist contractData.call_value.
    rows = [_trigger_row("s2", NOW, ADDR, 5_998_000_000, amount=0)]

    async def fake_get(params):
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert [t["amount_sun"] for t in out["transfers"]] == [5_998_000_000]


@pytest.mark.parametrize("call_value", [None, 0, "0", "kaputt"])
@pytest.mark.asyncio
async def test_trigger_contract_ohne_call_value_wird_ignoriert(monkeypatch, call_value):
    rows = [_trigger_row("s3", NOW, ADDR, call_value, method="transfer", amount=0)]

    async def fake_get(params):
        return {"total": 1, "data": rows}
    monkeypatch.setattr(th, "_get", fake_get)
    out = await th.fetch_transfers(ADDR)
    assert out["transfers"] == []
