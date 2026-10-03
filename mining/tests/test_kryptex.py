"""Kryptex-Abruf gegen einen Fake-Server (httpx.MockTransport) — kein echter Traffic."""
from __future__ import annotations

import httpx
import pytest
from backend import kryptex

INDEX = {
    "rvn": {"algo": "KawPow", "device_types": ["gpu"]},
    "xel": {"algo": "Xelishash", "device_types": ["gpu"]},
    "btc": {"algo": "SHA-256", "device_types": ["asic"]},
    "../evil": {"device_types": ["gpu"]},
}
POOL = {
    "rvn": {"name": "Ravencoin", "algo": "KawPow", "fee": 0.01, "fee_type": "PPS+",
            "net_hashrate": 6.5e11, "estimated_profit_day": 2.5e-6},
    "xel": {"name": "Xelis", "algo": "Xelishash", "fee": 0.01, "fee_type": "PROP",
            "net_hashrate": 1.0e8, "estimated_profit_day": None},
}


def _client(fail: set[str] | None = None, index_status: int = 200) -> httpx.AsyncClient:
    fail = fail or set()

    def handler(req: httpx.Request) -> httpx.Response:
        p = req.url.path
        if p == "/api/v1/index":
            return httpx.Response(index_status, json=INDEX)
        for coin, pool in POOL.items():
            if coin in fail and coin in p:
                return httpx.Response(500)
            if p == f"/{coin}/api/v1/pool/info":
                return httpx.Response(200, json=pool)
            if p == f"/api/v1/coin/{coin}/info":
                return httpx.Response(200, json={"daily_emission": 5000.0})
            if p == f"/api/v1/coin/{coin}/price/chart":
                assert req.url.params["time_range"] == "day"
                return httpx.Response(200, json=[{"price": 9.0}, {"price": 0.5}])
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=kryptex.BASE)


def test_gpu_coins_filters_device_and_invalid_ticker():
    assert kryptex.gpu_coins(INDEX) == ["rvn", "xel"]


async def test_fetch_quotes_normalizes():
    quotes = {q.coin: q for q in await kryptex.fetch_quotes(_client())}
    assert set(quotes) == {"rvn", "xel"}
    rvn, xel = quotes["rvn"], quotes["xel"]
    assert rvn.profit_per_hs_day == 2.5e-6 and rvn.estimated is False
    assert rvn.price_usd == 0.5  # letzter Punkt der Kurve
    assert xel.estimated is True  # Fallback aus daily_emission
    assert xel.profit_per_hs_day == pytest.approx(5000.0 / 1.0e8 * 0.99)
    assert xel.fee_type == "PROP"


async def test_single_coin_failure_does_not_break_others():
    quotes = await kryptex.fetch_quotes(_client(fail={"xel"}))
    assert [q.coin for q in quotes] == ["rvn"]


async def test_index_failure_raises():
    with pytest.raises(kryptex.KryptexError):
        await kryptex.fetch_quotes(_client(index_status=503))
