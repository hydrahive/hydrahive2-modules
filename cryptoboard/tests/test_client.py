"""C1 — CoinGecko-Client: Transform-Helfer (über gemocktem _get, kein Netz)."""
from __future__ import annotations

import pytest

from backend import client


@pytest.fixture
def fake_get(monkeypatch):
    def _install(payload):
        async def _get(path, params=None):
            _get.calls.append((path, params))
            return payload
        _get.calls = []
        monkeypatch.setattr(client, "_get", _get)
        return _get
    return _install


async def test_search_flacht_coins_ab(fake_get):
    fake_get({"coins": [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1, "thumb": "x.png"},
        {"id": "eth", "symbol": "eth", "name": "Ethereum", "market_cap_rank": 2, "thumb": "y.png"},
    ]})
    out = await client.search("bit")
    assert out[0] == {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "market_cap_rank": 1, "thumb": "x.png"}
    assert len(out) == 2


async def test_markets_mappt_felder_und_sparkline(fake_get):
    g = fake_get([{
        "id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "image": "b.png",
        "current_price": 90000, "market_cap": 1_700_000, "market_cap_rank": 1,
        "total_volume": 50000,
        "price_change_percentage_24h_in_currency": 1.5,
        "price_change_percentage_7d_in_currency": -3.2,
        "sparkline_in_7d": {"price": [1, 2, 3]},
    }])
    out = await client.markets("eur", ids=["bitcoin"])
    assert out[0]["symbol"] == "BTC"
    assert out[0]["price"] == 90000
    assert out[0]["change_24h"] == 1.5
    assert out[0]["change_7d"] == -3.2
    assert out[0]["sparkline"] == [1, 2, 3]
    # ids → komma-joined param
    assert g.calls[0][1]["ids"] == "bitcoin"


async def test_markets_top_setzt_order(fake_get):
    g = fake_get([])
    await client.markets("usd", top=10)
    params = g.calls[0][1]
    assert params["order"] == "market_cap_desc"
    assert params["per_page"] == "10"


async def test_market_chart_liefert_prices(fake_get):
    fake_get({"prices": [[1000, 90], [2000, 91]]})
    out = await client.market_chart("bitcoin", "eur", "7")
    assert out == [[1000, 90], [2000, 91]]


async def test_coin_detail_zieht_waehrung(fake_get):
    fake_get({
        "id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
        "image": {"large": "big.png"},
        "description": {"en": "digital gold"},
        "links": {"homepage": ["https://bitcoin.org", ""]},
        "market_data": {
            "current_price": {"eur": 90000, "usd": 98000},
            "market_cap": {"eur": 1_700_000},
            "market_cap_rank": 1,
            "total_volume": {"eur": 50000},
            "price_change_percentage_24h": 1.5,
            "price_change_percentage_7d": -3.2,
            "ath": {"eur": 100000},
            "atl": {"eur": 50},
            "circulating_supply": 19_000_000,
            "total_supply": 21_000_000,
            "max_supply": 21_000_000,
        },
    })
    out = await client.coin_detail("bitcoin", "eur")
    assert out["price"] == 90000  # eur, nicht usd
    assert out["ath"] == 100000
    assert out["homepage"] == "https://bitcoin.org"
    assert out["description"] == "digital gold"


async def test_helfer_tolerieren_leere_payloads(fake_get):
    fake_get(None)
    assert await client.search("x") == []
    fake_get("nicht-dict")
    assert await client.coin_detail("x", "eur") == {}
