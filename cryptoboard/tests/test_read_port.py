"""Read-Port — schmale, explizite Lese-Fassade für andere Module (siehe backend/read_port.py Docstring).

Prüft: eigene Daten sichtbar, fremder User bekommt nie fremde Daten (leer/eigenes
"default"), unbekannte portfolio_id -> PortfolioNotFound, Integer-Cent-Rundung
(ROUND_HALF_EVEN über Decimal(str(x))), Kursausfall -> complete=False/
PortfolioUnavailable, trades() liefert keine Floats für Geld.

Netz (CoinGecko) wird wie in den bestehenden Portfolio-/Valuation-Tests gemockt
(monkeypatch auf backend.client), kein echter Traffic.
"""
from __future__ import annotations

from datetime import date

import pytest

from backend import client as cg
from backend import portfolio_store as store
from backend import read_port


def _add_tx(user, coin="bitcoin", symbol="BTC", name="Bitcoin", kind="buy",
            qty=1.0, price=100.0, fee=0.0, at="2020-01-01T00:00:00Z"):
    return store.add(
        user, coin_id=coin, symbol=symbol, name=name, kind=kind,
        quantity=qty, price=price, fee=fee, executed_at=at, note="",
    )


@pytest.fixture
def mock_markets(monkeypatch):
    """Statischer Kurs: bitcoin=100.0 EUR (analog test_portfolio.py)."""
    async def fake_markets(vs, *, ids=None, top=None):
        prices = {"bitcoin": {"id": "bitcoin", "price": 100.0, "image": None, "change_24h": 0.0}}
        return [prices[i] for i in (ids or []) if i in prices]
    monkeypatch.setattr(cg, "markets", fake_markets)


@pytest.fixture
def mock_markets_down(monkeypatch):
    """Kein Kurs lieferbar — simuliert Ausfall der Kursquelle (wie client._prices
    bereits intern Exceptions abfängt und eine leere Liste behandelt)."""
    async def fake_markets(vs, *, ids=None, top=None):
        return []
    monkeypatch.setattr(cg, "markets", fake_markets)


# ---------------------------------------------------------------- portfolios_for
def test_portfolios_for_liefert_immer_default(client):
    assert read_port.portfolios_for("testuser") == [
        {"id": "default", "label": "Portfolio", "currency": "EUR"}
    ]


def test_portfolios_for_auch_ohne_transaktionen(client):
    # "leer, wenn der User keine Transaktionen hat? -> trotzdem 'default' liefern"
    assert read_port.portfolios_for("ohne-daten") == [
        {"id": "default", "label": "Portfolio", "currency": "EUR"}
    ]


# ---------------------------------------------------------------- portfolio_value
async def test_portfolio_value_eigene_daten_sichtbar(client, mock_markets):
    _add_tx("testuser", qty=2.0, price=50.0)  # Cost-Basis 100, aktueller Kurs 100 -> Wert 200
    out = await read_port.portfolio_value("testuser", "default")
    assert out["portfolio_id"] == "default"
    assert out["currency"] == "EUR"
    assert out["value_minor"] == 20000  # 200.00 EUR
    assert out["complete"] is True
    assert out["position_count"] == 1
    assert "as_of" in out and out["as_of"].endswith("Z")


async def test_portfolio_value_fremder_user_sieht_nichts(client, mock_markets):
    """Transaktionen von 'testuser' dürfen bei Abfrage für 'other' nicht auftauchen."""
    _add_tx("testuser", qty=5.0, price=100.0)
    out = await read_port.portfolio_value("other", "default")
    assert out["value_minor"] == 0
    assert out["position_count"] == 0


async def test_portfolio_value_unbekannte_portfolio_id(client, mock_markets):
    with pytest.raises(read_port.PortfolioNotFound):
        await read_port.portfolio_value("testuser", "nicht-default")


async def test_portfolio_value_integer_cent_rundung_half_even(client, mock_markets):
    # 1.2345 Stück * 100 EUR = 123.45 EUR -> exakt 12345 Cent, keine Rundung nötig
    _add_tx("testuser", qty=1.2345, price=100.0)
    out = await read_port.portfolio_value("testuser", "default")
    assert out["value_minor"] == 12345


async def test_portfolio_value_kursausfall_complete_false(client, mock_markets_down):
    """Offene Position ohne lieferbaren Kurs -> complete=False, kein Crash."""
    _add_tx("testuser", qty=1.0, price=50.0)
    out = await read_port.portfolio_value("testuser", "default")
    assert out["complete"] is False
    # Ohne Kurs ist der Wert der offenen Position 0 (siehe portfolio.summary()).
    assert out["value_minor"] == 0


async def test_portfolio_value_ohne_offene_position_ist_complete(client, mock_markets_down):
    """Keine Transaktionen -> keine offene Position -> complete bleibt True
    (es fehlt kein Kurs, weil keiner gebraucht wird)."""
    out = await read_port.portfolio_value("leer-user", "default")
    assert out["complete"] is True
    assert out["value_minor"] == 0


# ---------------------------------------------------------------- trades
def test_trades_eigene_daten_sichtbar(client):
    _add_tx("testuser", coin="bitcoin", kind="buy", qty=1.5, price=200.0, fee=1.0, at="2020-01-01T00:00:00Z")
    rows = read_port.trades("testuser", "default")
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "buy"
    assert row["coin_id"] == "bitcoin"
    assert row["symbol"] == "BTC"
    assert row["quantity"] == "1.5"
    assert row["gross_minor"] == 30000  # 1.5 * 200 = 300.00 EUR
    assert row["fee_minor"] == 100       # 1.00 EUR
    assert row["executed_at"] == "2020-01-01T00:00:00Z"
    assert row["ref"].startswith("cb:")


def test_trades_fremder_user_sieht_leere_liste(client):
    _add_tx("testuser", qty=1.0, price=100.0)
    assert read_port.trades("other", "default") == []


def test_trades_unbekannte_portfolio_id(client):
    with pytest.raises(read_port.PortfolioNotFound):
        read_port.trades("testuser", "irgendwas")


def test_trades_chronologisch_sortiert(client):
    _add_tx("testuser", coin="bitcoin", at="2020-02-01T00:00:00Z", qty=1.0, price=1.0)
    _add_tx("testuser", coin="bitcoin", at="2020-01-01T00:00:00Z", qty=1.0, price=1.0)
    rows = read_port.trades("testuser", "default")
    assert [r["executed_at"] for r in rows] == ["2020-01-01T00:00:00Z", "2020-02-01T00:00:00Z"]


def test_trades_since_filtert(client):
    _add_tx("testuser", coin="bitcoin", at="2020-01-01T00:00:00Z", qty=1.0, price=1.0)
    _add_tx("testuser", coin="bitcoin", at="2020-06-01T00:00:00Z", qty=1.0, price=1.0)
    rows = read_port.trades("testuser", "default", since="2020-03-01")
    assert len(rows) == 1
    assert rows[0]["executed_at"] == "2020-06-01T00:00:00Z"


def test_trades_limit_greift(client):
    for i in range(5):
        _add_tx("testuser", coin="bitcoin", at=f"2020-01-0{i + 1}T00:00:00Z", qty=1.0, price=1.0)
    rows = read_port.trades("testuser", "default", limit=2)
    assert len(rows) == 2


def test_trades_keine_floats_fuer_geld(client):
    """gross_minor/fee_minor müssen int sein; quantity ein Decimal-fähiger String,
    kein float — sonst könnte das Haushaltsbuch Rundungsfehler übernehmen."""
    _add_tx("testuser", coin="bitcoin", qty=0.1, price=3.0, fee=0.01, at="2020-01-01T00:00:00Z")
    row = read_port.trades("testuser", "default")[0]
    assert isinstance(row["gross_minor"], int)
    assert isinstance(row["fee_minor"], int)
    assert isinstance(row["quantity"], str)
    assert not isinstance(row["quantity"], float)
    # String muss als Decimal parsebar sein (Vertrag: Decimal-String).
    from decimal import Decimal
    Decimal(row["quantity"])


def test_trades_import_hash_durchgereicht(client):
    store.add(
        "testuser", coin_id="bitcoin", symbol="BTC", name="Bitcoin", kind="buy",
        quantity=1.0, price=1.0, fee=0.0, executed_at="2020-01-01T00:00:00Z",
        note="", import_hash="abc123",
    )
    row = read_port.trades("testuser", "default")[0]
    assert row["import_hash"] == "abc123"


def test_trades_import_hash_none_wenn_fehlt(client):
    _add_tx("testuser", at="2020-01-01T00:00:00Z")
    row = read_port.trades("testuser", "default")[0]
    assert row["import_hash"] is None


# ---------------------------------------------------------------- value_series
async def test_value_series_eigene_daten(client):
    from backend import price_history_store as price_store
    _add_tx("testuser", coin="bitcoin", kind="transfer_in", qty=1.0, price=0.0, at="2020-01-01T00:00:00Z")
    price_store.upsert_series("bitcoin", {"2020-01-15": 100.0, "2020-01-31": 200.0, "2020-02-15": 300.0})
    out = await read_port.value_series(
        "testuser", "default", start=date(2020, 1, 1), end=date(2020, 2, 28),
    )
    months = {p["month"] for p in out}
    assert "2020-01" in months
    assert "2020-02" in months
    jan = next(p for p in out if p["month"] == "2020-01")
    assert jan["value_minor"] == 20000  # 1 BTC * 200 EUR am letzten Tag mit Kurs im Januar
    for p in out:
        assert isinstance(p["value_minor"], int)


async def test_value_series_fremder_user_sieht_nichts(client):
    from backend import price_history_store as price_store
    _add_tx("testuser", coin="bitcoin", kind="transfer_in", qty=1.0, price=0.0, at="2020-01-01T00:00:00Z")
    price_store.upsert_series("bitcoin", {"2020-01-15": 100.0})
    out = await read_port.value_series(
        "other", "default", start=date(2020, 1, 1), end=date(2020, 1, 31),
    )
    assert out == []


async def test_value_series_unbekannte_portfolio_id(client):
    with pytest.raises(read_port.PortfolioNotFound):
        await read_port.value_series(
            "testuser", "woanders", start=date(2020, 1, 1), end=date(2020, 1, 31),
        )


async def test_value_series_ohne_transaktionen_leer(client):
    out = await read_port.value_series(
        "testuser", "default", start=date(2020, 1, 1), end=date(2020, 1, 31),
    )
    assert out == []


# ---------------------------------------------------------------- PORT_VERSION
def test_port_version_ist_3():
    # v3 (Etappe B, VERTRAG-B.md Punkt 3): ledger_moves kam hinzu, v1/v2-Funktionen
    # bleiben unveraendert (siehe restliche Tests in dieser Datei + test_read_port_wallets.py).
    assert read_port.PORT_VERSION == 3
