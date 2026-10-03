"""E5: Energie-Steuerung — Plan, Mindestzeit, Quelle, nur LAN."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend import catalog, power, power_source, store
from backend.profit import CoinQuote

P = "/api/modules/mining"
D = "/api/module-device/mining"
INFO = {"gpu_vendor": "nvidia", "gpu_model": "RTX 5060 Ti"}


@pytest.fixture(autouse=True)
def _reset():
    try:
        from hydrahive.api.middleware import inbound_ratelimit
        inbound_ratelimit.reset()
    except ImportError:
        pass
    power._state.update(watts=None, ok_at=None)
    yield
    power._state.update(watts=None, ok_at=None)


@pytest.fixture
def quotes():
    store.replace_quotes([CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])


def _rig(client, admin_headers, name="r1", approve=True) -> dict:
    code = client.post(f"{P}/rigs/pairing", headers=admin_headers, json={"name": name}).json()["code"]
    e = client.post(f"{D}/enroll", headers={"X-Pairing-Code": code}, json={"info": INFO}).json()
    if approve:
        client.post(f"{P}/rigs/{e['rig_id']}/approve", headers=admin_headers)
    return e


def _report(client, e, state=None):
    r = client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                    json={"info": INFO, "state": state or {"miner": "idle"}})
    assert r.status_code == 200, r.text
    return r.json()["desired"]


# ---- Energie ----
def _r(id_, w=200, follows=1, prio=0, vpw=0.0):
    return {"id": id_, "name": id_, "follows_power": follows, "priority": prio,
            "last_report_obj": {"power_w": w}, "_value_per_watt": vpw}


def test_plan_fits_budget_by_priority():
    rigs = [_r("a", 200), _r("b", 200), _r("z", 200, prio=5)]
    assert power.plan(rigs, 450) == {"z", "a"}           # z hat Vorrang, obwohl alphabetisch zuletzt
    assert power.plan(rigs, 150) == set()


def test_plan_prefers_value_per_watt_at_same_priority():
    rigs = [_r("a", 200, vpw=0.001), _r("b", 200, vpw=0.009)]
    assert power.plan(rigs, 250) == {"b"}


def test_plan_non_followers_always_on_and_count():
    rigs = [_r("fix", 300, follows=0), _r("a", 200)]
    assert power.plan(rigs, 400) == {"fix"}
    assert power.plan(rigs, 500) == {"fix", "a"}


def test_rig_watts_default_when_unknown():
    assert power.rig_watts({"last_report_obj": {}}) == power.DEFAULT_RIG_WATTS
    assert power.rig_watts({"last_report_obj": {"power_w": 12}}) == power.DEFAULT_RIG_WATTS  # Leerlauf zählt nicht


def test_budget_off_respects_min_time_when_coming_back(client, admin_headers, quotes):
    """Budget-aus → Budget-an innerhalb der Mindestzeit: bleibt aus (gegen Flattern)."""
    store.update_config({"kryptex_user": "krxTEST", "power_mode": "fixed", "power_fixed_w": 0})
    e = _rig(client, admin_headers)
    power.refresh()
    assert _report(client, e)["reason"] == "power_budget"
    store.update_config({"power_fixed_w": 5000})
    power.refresh()
    assert _report(client, e)["reason"] == "power_budget"


def test_power_fixed_zero_stops_and_off_resumes(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST", "power_mode": "fixed", "power_fixed_w": 0})
    e = _rig(client, admin_headers)
    power.refresh()
    assert _report(client, e)["reason"] == "power_budget"
    store.update_config({"power_mode": "off"})
    assert _report(client, e)["action"] == "benchmark"


def test_power_source_unreachable_stops(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST", "power_mode": "fixed", "power_fixed_w": 5000})
    e = _rig(client, admin_headers)
    assert _report(client, e)["reason"] == "power_source_down"     # noch nie gelesen → aus
    power.refresh()
    assert _report(client, e)["action"] == "benchmark"              # Werte da → sofort an (keine Mindestzeit)


def test_power_min_minutes_prevents_flapping(client, admin_headers, quotes, monkeypatch):
    store.update_config({"kryptex_user": "krxTEST", "power_mode": "fixed", "power_fixed_w": 5000})
    e = _rig(client, admin_headers)
    power.refresh()
    assert _report(client, e)["action"] == "benchmark"              # an
    store.update_config({"power_fixed_w": 0})
    power.refresh()
    assert _report(client, e)["action"] == "benchmark"              # Wolke: bleibt an (< 10 min)
    later = datetime.now(timezone.utc) + timedelta(minutes=11)
    power._state["ok_at"] = later
    rig = {**client.get(f"{P}/rigs", headers=admin_headers).json()[0], "follows_power": 1}
    assert power.allowed(rig, now=later)[:2] == (False, True)        # nach 10 min: aus


def test_rig_not_following_power_ignores_budget(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST", "power_mode": "fixed", "power_fixed_w": 0})
    e = _rig(client, admin_headers)
    assert client.post(f"{P}/rigs/{e['rig_id']}/power", headers=admin_headers,
                       json={"follows_power": False, "priority": 0}).status_code == 200
    power.refresh()
    assert _report(client, e)["action"] == "benchmark"
    assert client.post(f"{P}/rigs/{e['rig_id']}/power", headers=admin_headers,
                       json={"follows_power": "ja", "priority": 0}).status_code == 400


@pytest.mark.parametrize("url", ["http://8.8.8.8/x", "https://example.org/p", "file:///etc/passwd",
                                 "http://127.0.0.1/x", "http://user:pw@192.168.1.5/", "http://169.254.169.254/"])
def test_power_url_must_be_lan(client, admin_headers, url):
    assert client.put(f"{P}/config", headers=admin_headers, json={"power_url": url}).status_code == 400


def test_power_url_lan_ok_and_json_path():
    assert power_source.validate_url("http://192.168.178.50/api") == "http://192.168.178.50/api"
    assert power_source.validate_url("http://pv.local/x") == "http://pv.local/x"
    assert power_source._json_path({"data": {"pv": [1, {"w": 7}]}}, "data.pv.1.w") == 7
    assert power_source._json_path({"a": 1}, "a.b") is None


def test_power_status_route(client, admin_headers, user_headers):
    assert client.get(f"{P}/rigs/power", headers=user_headers).status_code == 403
    assert client.get(f"{P}/rigs/power", headers=admin_headers).json()["mode"] == "off"
