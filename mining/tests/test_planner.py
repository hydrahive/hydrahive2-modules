"""E3: Benchmark-Ablauf und Zuteilung über die echte Geräte-Route."""
from __future__ import annotations

import pytest

from backend import catalog, planner, power, runtime_store, store
from backend.profit import CoinQuote

P = "/api/modules/mining"
D = "/api/module-device/mining"
INFO = {"gpu_vendor": "nvidia", "gpu_model": "RTX 5060 Ti", "client_version": "0.4.0"}


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


def test_no_user_means_stop(client, admin_headers, quotes):
    assert _report(client, _rig(client, admin_headers))["reason"] == "no_kryptex_user"


def test_benchmark_job_has_only_names(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    d = _report(client, _rig(client, admin_headers))
    assert d["action"] == "benchmark" and d["seconds"] == planner.BENCH_SECONDS
    assert set(d["job"]) == {"coin", "miner", "algo", "user", "worker", "region", "version"}
    assert d["job"]["worker"] == "r1" and d["job"]["user"] == "krxTEST"
    assert "url" not in str(d) and "args" not in d["job"]


def test_full_benchmark_cycle_then_mine_best(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    d = _report(client, e)
    seen = 0
    while d["action"] == "benchmark":
        j = d["job"]
        hr = 9e6 if (j["coin"], j["miner"]) == ("cfx", "lolminer") else 1e6
        d = _report(client, e, {"benchmark_result": {"coin": j["coin"], "miner": j["miner"], "hashrate": hr, "watts": 150}})
        seen += 1
        assert seen < 50
    assert seen == sum(len(catalog.options(c, "nvidia")) for c in catalog.coins())
    assert (d["action"], d["job"]["coin"], d["job"]["miner"]) == ("mine", "cfx", "lolminer")
    log = client.get(f"{P}/rigs/log", headers=admin_headers).json()
    assert log[0]["to_coin"] == "mine:cfx"


def test_benchmark_result_for_other_job_is_ignored(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    first = _report(client, e)["job"]
    _report(client, e, {"benchmark_result": {"coin": "prl", "miner": "srbminer", "hashrate": 5e20}})
    assert runtime_store.bench_for(e["rig_id"]) == ({}, set())
    assert _report(client, e)["job"]["coin"] == first["coin"]


def test_failed_benchmark_is_recorded_and_skipped(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    j = _report(client, e)["job"]
    nxt = _report(client, e, {"benchmark_result": {"coin": j["coin"], "miner": j["miner"], "hashrate": None, "error": "x"}})
    assert (nxt["job"]["coin"], nxt["job"]["miner"]) != (j["coin"], j["miner"])
    assert runtime_store.bench_for(e["rig_id"])[1] == {(j["coin"], j["miner"])}


def test_benchmark_reset_and_list(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    j = _report(client, e)["job"]
    _report(client, e, {"benchmark_result": {"coin": j["coin"], "miner": j["miner"], "hashrate": 1e6}})
    assert len(client.get(f"{P}/rigs/{e['rig_id']}/benchmarks", headers=admin_headers).json()) == 1
    client.post(f"{P}/rigs/{e['rig_id']}/benchmarks/reset", headers=admin_headers)
    assert client.get(f"{P}/rigs/{e['rig_id']}/benchmarks", headers=admin_headers).json() == []


def test_delete_forgets_runtime(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e)
    client.post(f"{P}/rigs/{e['rig_id']}/revoke", headers=admin_headers)
    client.delete(f"{P}/rigs/{e['rig_id']}", headers=admin_headers)
    assert runtime_store.get_assignment(e["rig_id"]) == (None, None, None)


def test_stop_when_offline_flag(client, admin_headers, quotes):
    e = _rig(client, admin_headers)
    assert client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                       json={"state": {}}).json()["desired"]["stop_when_offline"] is False
    store.update_config({"power_mode": "fixed"})
    assert client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                       json={"state": {}}).json()["desired"]["stop_when_offline"] is True


def test_absurd_benchmark_hashrate_is_rejected(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    j = _report(client, e)["job"]
    _report(client, e, {"benchmark_result": {"coin": j["coin"], "miner": j["miner"], "hashrate": 1e30}})
    assert runtime_store.bench_for(e["rig_id"]) == ({}, {(j["coin"], j["miner"])})


def test_rig_list_reports_benchmark_progress(client, admin_headers, quotes):
    """Die Oberfläche zeigt „Benchmark x/y“ — y kommt vom Server aus dem Katalog."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    j = _report(client, e)["job"]
    _report(client, e, {"benchmark_result": {"coin": j["coin"], "miner": j["miner"], "hashrate": 1e6}})
    (row,) = client.get(f"{P}/rigs", headers=admin_headers).json()
    total = sum(len(catalog.options(c, "nvidia")) for c in catalog.coins())
    assert (row["bench_done"], row["bench_failed"], row["bench_total"]) == (1, 0, total)
    assert row["assignment"]["mode"] == "benchmark"
