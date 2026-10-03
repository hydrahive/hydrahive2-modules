"""Verlauf für das Diagramm: Proben speichern (1/min, 7 Tage), ausdünnen, Route."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend import catalog, history, runtime_store, store
from backend.decide import Assignment
from backend.profit import CoinQuote

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
RIG = {"id": "r1", "name": "rig-01"}


@pytest.fixture
def quotes():
    store.replace_quotes([CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])


def _state(hr=5e7, cards=((60.0, 150.0, 99.0),)):
    return {"hashrate": hr, "gpus": [{"temp_c": t, "power_w": w, "util_pct": u} for t, w, u in cards]}


def _mine(coin="cfx", miner="rigel"):
    runtime_store.set_assignment("r1", Assignment("mine", coin, miner, "octopus", "best"), None, power_changed=False)


def test_sample_contains_earnings_percent_and_cards(quotes):
    _mine()
    runtime_store.save_bench("r1", "cfx", "rigel", "octopus", 4e7, 140.0, None)
    history.record(RIG, _state(hr=5e7, cards=((60.0, 150.0, 99.0), (64.0, 160.0, 98.0))), now=T0)
    (p,) = history.points("r1", since=T0 - timedelta(hours=1))
    assert p["coin"] == "cfx" and p["mode"] == "mine"
    assert p["usd_day"] == pytest.approx(1e-6 * 5e7 * 1.0)
    assert p["pct"] == pytest.approx(125.0)                       # 5e7 von 4e7 gemessen
    assert [c["power_w"] for c in p["cards"]] == [150.0, 160.0]


def test_at_most_one_sample_per_minute(quotes):
    _mine()
    for s in (0, 30, 59):
        history.record(RIG, _state(), now=T0 + timedelta(seconds=s))
    history.record(RIG, _state(), now=T0 + timedelta(seconds=61))
    assert len(history.points("r1", since=T0 - timedelta(hours=1))) == 2


def test_samples_older_than_seven_days_are_pruned(quotes):
    _mine()
    history.record(RIG, _state(), now=T0 - timedelta(days=8))
    history.record(RIG, _state(), now=T0 - timedelta(days=6))
    history.record(RIG, _state(), now=T0)           # schreibt + räumt auf
    assert len(history.points("r1", since=T0 - timedelta(days=30))) == 2


def test_no_earnings_when_stopped_or_benchmarking(quotes):
    runtime_store.set_assignment("r1", Assignment("benchmark", "cfx", "rigel", "octopus", "b"), None,
                                 power_changed=False)
    history.record(RIG, _state(hr=5e7), now=T0)
    runtime_store.set_assignment("r1", Assignment("stop", reason="disabled"), None, power_changed=False)
    history.record(RIG, _state(hr=None), now=T0 + timedelta(minutes=2))
    bench, stop = history.points("r1", since=T0 - timedelta(hours=1))
    assert bench["mode"] == "benchmark" and bench["usd_day"] is None and bench["pct"] is None
    assert stop["mode"] == "stop" and stop["usd_day"] is None


def test_garbage_from_rig_is_not_stored(quotes):
    _mine()
    history.record(RIG, {"hashrate": "viel", "gpus": [{"temp_c": "heiß", "power_w": -5, "util_pct": 1e9}] * 70},
                   now=T0)
    (p,) = history.points("r1", since=T0 - timedelta(hours=1))
    assert p["usd_day"] is None
    assert len(p["cards"]) == 64                                   # Deckel
    assert p["cards"][0] == {"temp_c": None, "power_w": None, "util_pct": None}


def test_downsample_keeps_shape_and_last_coin():
    pts = [{"ts": f"t{i}", "mode": "mine", "coin": "cfx" if i < 5 else "erg", "usd_day": float(i), "pct": 100.0,
            "cards": [{"temp_c": 60.0 + i, "power_w": 100.0, "util_pct": None}]} for i in range(10)]
    out = history.downsample(pts, 5)
    assert len(out) == 5
    assert out[0]["usd_day"] == pytest.approx(0.5) and out[-1]["coin"] == "erg"
    assert out[2]["coin"] == "erg" and out[2]["ts"] == "t5"     # Fenster t4 (cfx), t5 (erg) → letzter zählt
    assert out[0]["cards"][0]["temp_c"] == pytest.approx(60.5)
    assert history.downsample(pts, 50) == pts


def test_downsample_keeps_gaps_as_none():
    pts = [{"ts": "a", "mode": "stop", "coin": None, "usd_day": None, "pct": None, "cards": []}] * 4
    (b,) = history.downsample(pts, 1)
    assert b["usd_day"] is None and b["cards"] == []


def test_forget_rig_deletes_history(quotes):
    _mine()
    history.record(RIG, _state(), now=T0)
    runtime_store.forget_rig("r1")
    assert history.points("r1", since=T0 - timedelta(days=30)) == []


# ---- über die echten Routen ----
def test_report_writes_sample_and_route_returns_it(client, admin_headers, user_headers, quotes):
    from tests.test_planner import P, _report, _rig
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, {"miner": "idle", "hashrate": None, "gpus": [{"temp_c": 55.0, "power_w": 30.0}]})
    r = client.get(f"{P}/rigs/history?hours=24", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    (series,) = body["rigs"]
    assert series["name"] == "r1" and series["points"][0]["cards"][0]["temp_c"] == 55.0
    assert "usd_per_eur" in body
    assert client.get(f"{P}/rigs/history", headers=user_headers).status_code == 403


@pytest.mark.parametrize("hours", [0, -1, 169, "x"])
def test_history_route_rejects_bad_range(client, admin_headers, hours):
    from tests.test_planner import P
    assert client.get(f"{P}/rigs/history?hours={hours}", headers=admin_headers).status_code in (400, 422)


def test_revoked_rigs_are_not_in_history(client, admin_headers, quotes):
    from tests.test_planner import P, _report, _rig
    e = _rig(client, admin_headers)
    _report(client, e)
    client.post(f"{P}/rigs/{e['rig_id']}/revoke", headers=admin_headers)
    assert client.get(f"{P}/rigs/history", headers=admin_headers).json()["rigs"] == []


def test_pending_rig_writes_no_history(client, admin_headers, quotes):
    """Nicht freigegebene Rechner dürfen keinen Verlauf erzeugen (fremde Geräte im Netz)."""
    from tests.test_planner import _report, _rig
    e = _rig(client, admin_headers, approve=False)
    _report(client, e, {"miner": "idle", "gpus": [{"temp_c": 50.0}]})
    assert history.points(e["rig_id"], since=T0 - timedelta(days=30)) == []
