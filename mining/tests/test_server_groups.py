"""Server side of the vendor groups: decide per group, report per group, old clients unchanged."""
from __future__ import annotations

import pytest
from backend import catalog, groups, runtime_store, store
from backend.profit import CoinQuote
from tests.test_planner import P, _rig

MIXED_INFO = {"gpu_vendor": "mixed", "gpu_model": "RTX 3070 + RX 6800", "gpu_mem_mb": 8192, "client_version": "0.4.0"}


@pytest.fixture
def quotes():
    store.replace_quotes([CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])


def _state(nv=None, amd=None):
    g = {}
    if nv is not None:
        g["nvidia"] = {"gpu_count": 1, "gpu_mem_mb": 8192, "power_w": 150.0, **nv}
    if amd is not None:
        g["amd"] = {"gpu_count": 2, "gpu_mem_mb": 16384, "power_w": 400.0, **amd}
    return {"miner": "idle", "groups": g}


def _report(client, e, state, info=MIXED_INFO):
    from tests.test_planner import D
    r = client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                    json={"info": info, "state": state})
    assert r.status_code == 200, r.text
    return r.json()["desired"]


def test_group_keys():
    rig = {"id": "r1", "gpu_vendor": "mixed"}
    assert groups.keys(rig, _state(nv={}, amd={})) == {"nvidia": "r1#nvidia", "amd": "r1#amd"}
    assert groups.keys({"id": "r1", "gpu_vendor": "amd"}, {}) == {"amd": "r1"}       # old client
    assert groups.keys({"id": "r1", "gpu_vendor": "none"}, {}) == {}


def test_mixed_rig_gets_one_job_per_group(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    d = _report(client, e, _state(nv={}, amd={}))
    assert set(d["groups"]) == {"nvidia", "amd"}
    assert d["groups"]["nvidia"]["action"] == "benchmark" and d["groups"]["amd"]["action"] == "benchmark"
    nv_job, amd_job = d["groups"]["nvidia"]["job"], d["groups"]["amd"]["job"]
    assert [nv_job["miner"], nv_job["algo"]] in catalog.data()["coins"][nv_job["coin"]]["options"]["nvidia"]
    assert [amd_job["miner"], amd_job["algo"]] in catalog.data()["coins"][amd_job["coin"]]["options"]["amd"]


def test_benchmark_results_are_stored_per_group(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    d = _report(client, e, _state(nv={}, amd={}))
    amd_job = d["groups"]["amd"]["job"]
    _report(client, e, _state(nv={}, amd={"benchmark_result": {"coin": amd_job["coin"], "miner": amd_job["miner"],
                                                              "hashrate": 4e7, "watts": 380}}))
    amd_bench, _ = runtime_store.bench_for(f"{e['rig_id']}#amd")
    nv_bench, _ = runtime_store.bench_for(f"{e['rig_id']}#nvidia")
    assert amd_bench == {(amd_job["coin"], amd_job["miner"]): 4e7} and nv_bench == {}


def test_result_for_other_group_is_ignored(client, admin_headers, quotes):
    """An AMD measurement must not be credited to the NVIDIA group."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    d = _report(client, e, _state(nv={}, amd={}))
    amd_job = d["groups"]["amd"]["job"]
    nv_job = d["groups"]["nvidia"]["job"]
    assert (nv_job["coin"], nv_job["miner"]) != (amd_job["coin"], amd_job["miner"])
    _report(client, e, _state(nv={"benchmark_result": {"coin": amd_job["coin"], "miner": amd_job["miner"],
                                                      "hashrate": 4e7}}, amd={}))
    assert runtime_store.bench_for(f"{e['rig_id']}#nvidia") == ({}, set())
    assert runtime_store.bench_for(f"{e['rig_id']}#amd") == ({}, set())     # nicht von AMD gemessen


def test_mixed_rig_mines_different_coins_per_group(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    for v, best in (("nvidia", "qtc"), ("amd", "erg")):
        k = f"{e['rig_id']}#{v}"
        for coin in catalog.coins():
            for miner, algo in catalog.options(coin, v):
                runtime_store.save_bench(k, coin, miner, algo, 9e9 if coin == best else 1e3, 100.0, None)
    d = _report(client, e, _state(nv={}, amd={}))
    assert d["groups"]["nvidia"]["action"] == "mine" and d["groups"]["nvidia"]["job"]["coin"] == "qtc"
    assert d["groups"]["amd"]["action"] == "mine" and d["groups"]["amd"]["job"]["coin"] == "erg"


def test_old_single_vendor_client_unchanged(client, admin_headers, quotes):
    """Client 0.3.x: no state.groups, flat desired as before, measurements under the plain rig ID."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    d = _report(client, e, {"miner": "idle"}, info={"gpu_vendor": "nvidia", "gpu_mem_mb": 16311})
    assert d["action"] == "benchmark" and "job" in d
    j = d["job"]
    _report(client, e, {"miner": "benchmark", "benchmark_result": {"coin": j["coin"], "miner": j["miner"],
                                                                   "hashrate": 5e7}},
            info={"gpu_vendor": "nvidia", "gpu_mem_mb": 16311})
    assert runtime_store.bench_for(e["rig_id"])[0] == {(j["coin"], j["miner"]): 5e7}


def test_single_vendor_new_client_keeps_plain_key(client, admin_headers, quotes):
    """New client in a NVIDIA-only rig: groups = {nvidia} → plain key, existing measurements stay valid."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    runtime_store.save_bench(e["rig_id"], "cfx", "rigel", "octopus", 5e7, 150.0, None)
    _report(client, e, _state(nv={}), info={"gpu_vendor": "nvidia", "gpu_mem_mb": 8192})
    assert runtime_store.bench_for(e["rig_id"])[0][("cfx", "rigel")] == 5e7
    assert runtime_store.get_assignment(e["rig_id"])[0] is not None              # Zuteilung unter alter ID
    assert runtime_store.get_assignment(f"{e['rig_id']}#nvidia")[0] is None
    (row,) = client.get(f"{P}/rigs", headers=admin_headers).json()
    assert row["bench_done"] == 1                                                 # alte Messung zählt weiter


def test_rig_list_shows_groups(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, _state(nv={}, amd={}))
    (row,) = client.get(f"{P}/rigs", headers=admin_headers).json()
    assert {g["vendor"] for g in row["groups"]} == {"nvidia", "amd"}
    amd = next(g for g in row["groups"] if g["vendor"] == "amd")
    assert amd["assignment"]["mode"] == "benchmark" and amd["bench_total"] == 22


def test_rebench_and_delete_cover_all_groups(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, _state(nv={}, amd={}))
    runtime_store.save_bench(f"{e['rig_id']}#amd", "erg", "lolminer", "AUTOLYKOS2", 1e8, 300.0, None)
    client.post(f"{P}/rigs/{e['rig_id']}/benchmarks/reset", headers=admin_headers)
    assert runtime_store.bench_for(f"{e['rig_id']}#amd") == ({}, set())
    runtime_store.save_bench(f"{e['rig_id']}#nvidia", "qtc", "srbminer", "quantus", 1e8, 300.0, None)
    client.post(f"{P}/rigs/{e['rig_id']}/revoke", headers=admin_headers)
    client.delete(f"{P}/rigs/{e['rig_id']}", headers=admin_headers)
    assert runtime_store.bench_for(f"{e['rig_id']}#nvidia") == ({}, set())


def test_unknown_group_from_client_is_ignored(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    st = _state(nv={}, amd={})
    st["groups"]["intel"] = {"gpu_count": 1}
    d = _report(client, e, st)
    assert set(d["groups"]) == {"nvidia", "amd"}


def test_bench_list_covers_all_groups(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, _state(nv={}, amd={}))
    runtime_store.save_bench(f"{e['rig_id']}#amd", "erg", "lolminer", "AUTOLYKOS2", 1e8, 300.0, None)
    runtime_store.save_bench(f"{e['rig_id']}#nvidia", "qtc", "srbminer", "quantus", 2e8, 150.0, None)
    rows = client.get(f"{P}/rigs/{e['rig_id']}/benchmarks", headers=admin_headers).json()
    assert {(r["vendor"], r["coin"]) for r in rows} == {("amd", "erg"), ("nvidia", "qtc")}


def test_single_vendor_bench_list_has_no_foreign_rows(client, admin_headers, quotes):
    """Prefix match must not catch another rig whose ID starts the same."""
    runtime_store.save_bench("abc", "erg", "lolminer", "AUTOLYKOS2", 1e8, 300.0, None)
    runtime_store.save_bench("abcd#amd", "qtc", "srbminer", "quantus", 1e8, 300.0, None)
    runtime_store.save_bench("abc_x", "qtc", "srbminer", "quantus", 1e8, 300.0, None)
    assert [r["coin"] for r in runtime_store.list_bench("abc")] == ["erg"]
    runtime_store.clear_bench("abc")
    assert runtime_store.bench_for("abcd#amd")[0] and runtime_store.bench_for("abc_x")[0]


def test_history_sample_sums_groups(client, admin_headers, quotes):
    from backend import history
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    for v, coin, miner, algo in (("nvidia", "qtc", "srbminer", "quantus"), ("amd", "erg", "lolminer", "AUTOLYKOS2")):
        k = f"{e['rig_id']}#{v}"
        for c in catalog.coins():
            for m, a in catalog.options(c, v):
                runtime_store.save_bench(k, c, m, a, 9e9 if c == coin else 1e3, 100.0, None)
    st = _state(nv={"hashrate": 9e9}, amd={"hashrate": 4.5e9})
    _report(client, e, st)
    rig = {"id": e["rig_id"], "gpu_vendor": "mixed"}
    s = history._sample(rig, st)
    assert s["mode"] == "mine" and s["coin"] == "erg+qtc"
    assert s["usd_day"] == pytest.approx(9e9 * 1e-6 * 0.99 + 4.5e9 * 1e-6 * 0.99, rel=0.05)
