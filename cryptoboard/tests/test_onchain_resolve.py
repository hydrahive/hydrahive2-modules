"""onchain_resolve — coin_id-Auflösung (B1) und EUR-Tageskurs-Wahl (B2)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend import client, onchain_resolve as rs
from backend import price_history_store as price_store

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


@pytest.fixture(autouse=True)
def _clear_cache():
    rs.clear_contract_cache()
    yield
    rs.clear_contract_cache()


# ---------------------------------------------------------------- B1: coin_id-Auflösung


@pytest.mark.asyncio
async def test_natives_asset_aufloesung():
    out = await rs.resolve_coin_id("base", None, "ETH")
    assert out == {"coin_id": "ethereum", "name": "", "unresolved": False}


@pytest.mark.asyncio
async def test_bekannter_kontrakt_ohne_netzaufruf(monkeypatch):
    async def boom(*a, **kw):
        raise AssertionError("bekannter Kontrakt darf keinen Netzaufruf auslösen")
    monkeypatch.setattr(client, "contract", boom)
    out = await rs.resolve_coin_id("base", USDC_BASE, "USDC")
    assert out == {"coin_id": "usd-coin", "name": "USDC", "unresolved": False}


@pytest.mark.asyncio
async def test_unbekannter_kontrakt_nutzt_coingecko_suche(monkeypatch):
    calls = []

    async def fake_contract(platform, address):
        calls.append((platform, address))
        return {"id": "some-token", "symbol": "SMT", "name": "Some Token"}
    monkeypatch.setattr(client, "contract", fake_contract)
    unknown = "0x" + "7" * 40
    out = await rs.resolve_coin_id("base", unknown, "SMT")
    assert out == {"coin_id": "some-token", "name": "Some Token", "unresolved": False}
    assert calls == [("base", unknown)]


@pytest.mark.asyncio
async def test_unbekannter_kontrakt_nicht_bei_coingecko_ist_unresolved(monkeypatch):
    async def fake_contract(platform, address):
        return None
    monkeypatch.setattr(client, "contract", fake_contract)
    unknown = "0x" + "6" * 40
    out = await rs.resolve_coin_id("base", unknown, "MYSTERY")
    assert out["coin_id"] is None
    assert out["unresolved"] is True
    assert out["name"] == "MYSTERY"


@pytest.mark.asyncio
async def test_kontraktsuche_wird_gecacht_ein_netzaufruf_je_kontrakt(monkeypatch):
    calls = []

    async def fake_contract(platform, address):
        calls.append((platform, address))
        return {"id": "some-token", "symbol": "SMT", "name": "Some Token"}
    monkeypatch.setattr(client, "contract", fake_contract)
    unknown = "0x" + "5" * 40
    await rs.resolve_coin_id("base", unknown, "SMT")
    await rs.resolve_coin_id("base", unknown, "SMT")
    await rs.resolve_coin_id("base", unknown, "SMT")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_netzfehler_bei_kontraktsuche_ist_unresolved_kein_crash(monkeypatch):
    async def boom(platform, address):
        raise RuntimeError("netz kaputt")
    monkeypatch.setattr(client, "contract", boom)
    unknown = "0x" + "4" * 40
    out = await rs.resolve_coin_id("base", unknown, "X")
    assert out["unresolved"] is True
    assert out["coin_id"] is None


# ---------------------------------------------------------------- B2: Tageskurs-Wahl


def test_day_aus_iso_zeitstempel():
    assert rs._day("2026-06-15T12:30:00Z") == "2026-06-15"
    assert rs._day(None) is None
    assert rs._day("nonsense") is None


def test_price_pair_stablecoin_bevorzugt(db_price_series):
    db_price_series("usd-coin", {"2026-06-15": 0.92})
    db_price_series("ethereum", {"2026-06-15": 3000.0})
    sell_price, buy_price, preis_fehlt = rs.price_pair(
        "usd-coin", Decimal("1000"), "ethereum", Decimal("0.5"), "2026-06-15",
    )
    assert preis_fehlt is False
    assert sell_price == Decimal("0.92")
    # Wert = 1000*0.92 = 920 EUR -> buy_price = 920/0.5 = 1840
    assert buy_price == Decimal("1840")


def test_price_pair_kein_kurs_auf_keiner_seite(db_price_series):
    sell_price, buy_price, preis_fehlt = rs.price_pair(
        "unknown-coin", Decimal("10"), "other-coin", Decimal("5"), "2026-06-15",
    )
    assert sell_price is None
    assert buy_price is None
    assert preis_fehlt is True


def test_price_pair_nur_buy_seite_hat_kurs(db_price_series):
    db_price_series("ethereum", {"2026-06-15": 3000.0})
    sell_price, buy_price, preis_fehlt = rs.price_pair(
        "unknown-token", Decimal("100"), "ethereum", Decimal("1"), "2026-06-15",
    )
    assert preis_fehlt is False
    assert buy_price == Decimal("3000")
    assert sell_price == Decimal("30")  # 3000 / 100


def test_price_pair_weth_hat_vorrang_vor_sonstigem_aber_nicht_vor_stablecoin(db_price_series):
    db_price_series("weth", {"2026-06-15": 3000.0})
    db_price_series("usd-coin", {"2026-06-15": 0.92})
    sell_price, buy_price, preis_fehlt = rs.price_pair(
        "weth", Decimal("1"), "usd-coin", Decimal("3000"), "2026-06-15",
    )
    assert preis_fehlt is False
    # usd-coin (stable, rank 0) gewinnt gegen weth (rank 1)
    assert buy_price == Decimal("0.92")


@pytest.fixture
def db_price_series():
    def _set(coin_id, series):
        price_store.upsert_series(coin_id, series)
    return _set
