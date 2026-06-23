"""C5 — Automation: crypto_price-Trigger, crypto_threshold-Condition, Poller."""
from __future__ import annotations

import pytest

from hydrahive.butler.models import Flow, Node, NodePosition, TriggerEvent

from backend import alerts


@pytest.fixture(autouse=True)
def _reset_last_price():
    alerts._last_price.clear()
    yield
    alerts._last_price.clear()


def _ev(price, prev, coin="bitcoin") -> TriggerEvent:
    return TriggerEvent(event_type="crypto_price", payload={"coin_id": coin, "price": price, "prev_price": prev})


# ---- Trigger crypto_price ----

def test_trigger_matcht_coin():
    assert alerts.TRIGGER.matches({"coin_id": "bitcoin"}, _ev(1, 1)) is True


def test_trigger_anderer_coin_nein():
    assert alerts.TRIGGER.matches({"coin_id": "ethereum"}, _ev(1, 1, "bitcoin")) is False


def test_trigger_falscher_event_type_nein():
    e = TriggerEvent(event_type="cron", payload={})
    assert alerts.TRIGGER.matches({"coin_id": "bitcoin"}, e) is False


# ---- Condition crypto_threshold (Kreuzung) ----

def test_above_feuert_nur_am_uebertritt():
    # prev < 100k <= now → Kreuzung nach oben
    assert alerts.CONDITION.evaluate({"direction": "above", "price": "100000"}, _ev(101000, 99000)) is True
    # schon vorher drüber → kein neuer Übertritt
    assert alerts.CONDITION.evaluate({"direction": "above", "price": "100000"}, _ev(102000, 101000)) is False


def test_below_feuert_nur_am_uebertritt():
    assert alerts.CONDITION.evaluate({"direction": "below", "price": "100000"}, _ev(99000, 101000)) is True
    assert alerts.CONDITION.evaluate({"direction": "below", "price": "100000"}, _ev(98000, 99000)) is False


def test_threshold_ungueltiger_preis_false():
    assert alerts.CONDITION.evaluate({"direction": "above", "price": "abc"}, _ev(1, 1)) is False


def test_threshold_fehlende_event_daten_false():
    e = TriggerEvent(event_type="crypto_price", payload={"coin_id": "bitcoin", "price": 100})
    assert alerts.CONDITION.evaluate({"direction": "above", "price": "50"}, e) is False  # prev fehlt


# ---- Poller ----

def _flow(coin, enabled=True) -> Flow:
    node = Node(id="t", type="trigger", subtype="crypto_price",
                position=NodePosition(x=0, y=0), params={"coin_id": coin})
    return Flow(flow_id="f", name="Alert", owner="alice", enabled=enabled, nodes=[node])


def test_watched_coins_nur_aktive(monkeypatch):
    monkeypatch.setattr(alerts, "list_flows", lambda owner=None: [_flow("bitcoin"), _flow("ethereum", enabled=False)])
    assert alerts._watched_coins() == {"bitcoin"}


async def test_poll_trackt_prev_price(monkeypatch):
    monkeypatch.setattr(alerts, "list_flows", lambda owner=None: [_flow("bitcoin")])
    events: list = []

    async def fake_dispatch(event, *, owner=None, dry_run=False):
        events.append(event)
        return []

    monkeypatch.setattr(alerts, "dispatch_event", fake_dispatch)

    async def markets1(vs, *, ids=None, top=None):
        return [{"id": "bitcoin", "price": 90000, "change_24h": 1.0, "symbol": "BTC"}]

    monkeypatch.setattr(alerts.client, "markets", markets1)
    await alerts.poll()  # erster Poll → prev == price
    assert events[0].payload["coin_id"] == "bitcoin"
    assert events[0].payload["prev_price"] == 90000

    async def markets2(vs, *, ids=None, top=None):
        return [{"id": "bitcoin", "price": 101000, "change_24h": 2.0, "symbol": "BTC"}]

    monkeypatch.setattr(alerts.client, "markets", markets2)
    await alerts.poll()  # zweiter Poll → prev == alter Preis
    assert events[1].payload["prev_price"] == 90000
    assert events[1].payload["price"] == 101000


async def test_poll_ohne_coins_kein_dispatch(monkeypatch):
    monkeypatch.setattr(alerts, "list_flows", lambda owner=None: [])
    called: list = []

    async def fake_dispatch(event, *, owner=None, dry_run=False):
        called.append(event)

    monkeypatch.setattr(alerts, "dispatch_event", fake_dispatch)
    await alerts.poll()
    assert called == []


# ---- End-to-End register(ctx) ----

def test_register_verkabelt_alles():
    from hydrahive.modules.context import ModuleContext
    import backend

    ctx = ModuleContext("cryptoboard")
    backend.register(ctx)
    assert len(ctx.routers) == 4  # markt + watchlist + portfolio + analysis
    assert any(t.name == "query_crypto_price" for t in ctx.tools)
    assert any(s.subtype == "crypto_price" for s in ctx.butler_triggers)
    assert any(s.subtype == "crypto_threshold" for s in ctx.butler_conditions)
    assert any(j.name == "price_poll" for j in ctx.jobs)
    assert ctx.migrations_rel == "migrations"
