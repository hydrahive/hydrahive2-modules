"""Kurse werden nachgeladen, wenn ein Swap neuer ist als der gespeicherte Kurs.

Till 20.11.2026: „immer nachladen“. Vorher lud ensure_coins einen bereits
gecachten Coin nie neu – Swaps von heute/gestern bekamen „preis_fehlt“,
obwohl CoinGecko den Kurs hatte.
"""
from __future__ import annotations

import copy

import pytest

from backend import onchain_resolve as rs
from backend import price_history
from backend import price_history_store as ps

from tests.test_onchain_import_routes import DAY, H1, _preview

pytest_plugins = ["tests.test_onchain_import_routes"]

_REAL_ENSURE = price_history.ensure_coins  # vor jedem monkeypatch des setup-Fixtures

NEW_DAY = "2026-06-20"  # neuer als der Cache-Stand DAY = 2026-06-15


def _clear(*coin_ids: str) -> None:
    from hydrahive.db.connection import db
    with db() as c:
        for cid in coin_ids:
            c.execute("DELETE FROM module_cryptoboard_price_history WHERE coin_id = ?", (cid,))


def test_stale_coins_auswahl():
    _clear("rf-a", "rf-b", "rf-c")
    ps.upsert_series("rf-a", {"2026-06-15": 1.0})
    ps.upsert_series("rf-b", {"2026-06-25": 1.0})
    try:
        out = rs.stale_coins({"rf-a": "2026-06-20", "rf-b": "2026-06-20", "rf-c": "2026-06-01", "": "2026-06-01"})
        # rf-a: Cache älter als Swap → neu; rf-b: aktuell → nein; rf-c: gar nicht gecacht → neu
        assert out == ["rf-a", "rf-c"]
        assert rs.stale_coins({"rf-b": None}) == []         # ohne Tag: vorhandener Cache reicht
        assert rs.stale_coins({"rf-c": None}) == ["rf-c"]   # ohne Tag, nicht gecacht: laden
    finally:
        _clear("rf-a", "rf-b", "rf-c")


@pytest.mark.asyncio
async def test_aktueller_cache_kein_abruf(monkeypatch):
    _clear("rf-a")
    ps.upsert_series("rf-a", {"2026-06-25": 1.0})
    calls = []

    async def spy(ids, **kw):
        calls.append((list(ids), kw))
        return {}
    monkeypatch.setattr(price_history, "ensure_coins", spy)
    try:
        await rs.ensure_prices_cached({"rf-a": "2026-06-20"})
        assert calls == []                                    # nichts zu tun → kein Netzabruf
        await rs.ensure_prices_cached({"rf-a": "2026-06-30"})
        assert calls == [(["rf-a"], {"force": True})]         # veraltet → genau ein erzwungener Abruf
    finally:
        _clear("rf-a")


def test_preview_neuer_swap_laedt_kurs_nach(client, auth_headers, setup, monkeypatch):
    """Ganzer Weg: Swap vom NEW_DAY, Cache nur bis DAY → Nachladen → Preis statt preis_fehlt.

    Echte ensure_coins-Logik (setup ersetzt sie durch no_fetch → hier zurück auf das
    Original), nur der CoinGecko-Abruf fetch_coin ist ersetzt. So greift die alte
    Regel „gecacht = nie neu laden“ wirklich und der Test fällt ohne Fix."""
    monkeypatch.setattr(price_history, "ensure_coins", _REAL_ENSURE)
    fetched: list[str] = []

    async def fake_fetch_coin(coin_id):
        fetched.append(coin_id)
        prices = {"usd-coin": 0.95, "ethereum": 2100.0}
        return ps.upsert_series(coin_id, {NEW_DAY: prices[coin_id]}) if coin_id in prices else 0
    monkeypatch.setattr(price_history, "fetch_coin", fake_fetch_coin)

    from backend import alchemy_client as ac
    real_fetch = ac.fetch_transfers

    async def newer(chain, key, address, **kw):
        out = copy.deepcopy(await real_fetch(chain, key, address, **kw))  # gemeinsame Testdaten nicht verändern
        for t in out["transfers"]:
            if t.get("hash") == H1:
                t.setdefault("metadata", {})["blockTimestamp"] = f"{NEW_DAY}T12:00:00.000Z"
        return out
    monkeypatch.setattr(ac, "fetch_transfers", newer)
    try:
        tx = {t["hash"]: t for t in _preview(client, auth_headers, setup)["transactions"]}
        sell = tx[f"base:{H1}:sell"]
        assert sell["executed_at"].startswith(NEW_DAY)
        assert "usd-coin" in fetched and "ethereum" in fetched
        assert sell["price"] == "0.95" and not sell["preis_fehlt"]
    finally:
        _clear_new_day()


def _clear_new_day() -> None:
    from hydrahive.db.connection import db
    with db() as c:
        c.execute("DELETE FROM module_cryptoboard_price_history WHERE day = ?", (NEW_DAY,))


def test_tag_konstanten_passen():
    assert NEW_DAY > DAY
