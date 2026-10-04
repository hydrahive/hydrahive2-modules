"""Alte Rechner-Clients: nur Coins zuteilen, die sie kennen; Ablehnungen nicht dauerhaft merken.

Anlass: Client 0.3.x an Modul 0.6.0 bekam QTC zugeteilt, lehnte ab (unknown_coin)
und der Server merkte sich das als „fehlgeschlagen“ – auch nach dem Client-Update.
"""
from __future__ import annotations

import pytest
from backend import catalog, compat, runtime_store, store
from backend.profit import CoinQuote
from tests.test_planner import D, P, _rig

NEW_COINS = {"alph", "etc", "ethw", "octa", "qtc", "xtm-c29", "xtm-sha3x"}
OLD_COINS = set(catalog.coins()) - NEW_COINS


@pytest.fixture
def quotes():
    store.replace_quotes([CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])


def _report(client, e, version, state=None):
    info = {"gpu_vendor": "nvidia", "gpu_model": "RTX 3070", "gpu_mem_mb": 8192, "client_version": version}
    r = client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                    json={"info": info, "state": state or {"miner": "idle"}})
    assert r.status_code == 200, r.text
    return r.json()["desired"]


@pytest.mark.parametrize("version, expected", [
    ("0.3.1", OLD_COINS), ("0.3.0", OLD_COINS), (None, OLD_COINS), ("", OLD_COINS), ("kaputt", OLD_COINS),
    ("0.4.0", OLD_COINS | NEW_COINS), ("0.4.1", OLD_COINS | NEW_COINS), ("1.0", OLD_COINS | NEW_COINS),
    ("0.10.0", OLD_COINS | NEW_COINS), ("0.3.10", OLD_COINS),            # Zahlen, nicht Text vergleichen
])
def test_known_coins_per_client_version(version, expected):
    assert set(compat.known_coins(version)) == expected


def test_old_client_never_gets_new_coin(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    seen = set()
    for _ in range(60):                       # ganzer Benchmark-Durchlauf
        d = _report(client, e, "0.3.1")
        if d["action"] != "benchmark":
            break
        j = d["job"]
        seen.add(j["coin"])
        _report(client, e, "0.3.1", {"miner": "benchmark", "benchmark_result":
                                     {"coin": j["coin"], "miner": j["miner"], "hashrate": 1e6}})
    assert seen and not seen & NEW_COINS
    assert d["action"] == "mine" and d["job"]["coin"] in OLD_COINS


def test_old_client_rig_list_counts_only_known(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, "0.3.1")
    (row,) = client.get(f"{P}/rigs", headers=admin_headers).json()
    assert row["bench_total"] == sum(len(catalog.options(c, "nvidia")) for c in OLD_COINS
                                     if not (catalog.min_mem_mb(c) and 8192 < catalog.min_mem_mb(c)))


def test_rejection_is_skipped_until_client_update(client, admin_headers, quotes):
    """job_rejected bleibt gemerkt (sonst Endlosschleife: gleicher Auftrag, gleiche Ablehnung)."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    j = _report(client, e, "0.4.0")["job"]
    d = _report(client, e, "0.4.0", {"miner": "idle", "benchmark_result":
                                     {"coin": j["coin"], "miner": j["miner"], "hashrate": None,
                                      "error": "job_rejected:combination_not_allowed"}})
    assert (d["job"]["coin"], d["job"]["miner"]) != (j["coin"], j["miner"])


def test_client_update_retries_all_failures(client, admin_headers, quotes):
    """Altlasten aus 0.6.0 (job_rejected) und Miner-Abbrüche: nach Client-Update neu versuchen."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, "0.3.1")
    rid = e["rig_id"]
    runtime_store.save_bench(rid, "qtc", "srbminer", "quantus", None, None, "job_rejected:unknown_coin")
    runtime_store.save_bench(rid, "prl", "srbminer", "pearlhash", None, None, "watchdog:exited")
    runtime_store.save_bench(rid, "cfx", "rigel", "octopus", 5e7, 150.0, None)
    _report(client, e, "0.4.0")
    ok, failed = runtime_store.bench_for(rid)
    assert failed == set() and ok == {("cfx", "rigel"): 5e7}     # echte Messung bleibt


def test_first_report_after_update_uses_new_version(client, admin_headers, quotes):
    """Schon die erste Meldung des neuen Clients darf neue Coins bekommen."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, "0.3.1")
    for c in OLD_COINS:
        for m, a in catalog.options(c, "nvidia"):
            runtime_store.save_bench(e["rig_id"], c, m, a, 1e6, 100.0, None)
    assert _report(client, e, "0.3.1")["action"] == "mine"
    d = _report(client, e, "0.4.0")
    assert d["action"] == "benchmark" and d["job"]["coin"] in NEW_COINS


def test_old_client_rig_list_ignores_rejections_of_unknown_coins(client, admin_headers, quotes):
    """Altlast-Einträge für Coins, die der Client nicht kennt, verfälschen den Zähler nicht."""
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, "0.3.1")
    runtime_store.save_bench(e["rig_id"], "qtc", "srbminer", "quantus", None, None, "job_rejected:unknown_coin")
    (row,) = client.get(f"{P}/rigs", headers=admin_headers).json()
    assert row["bench_failed"] == 0


def test_same_version_keeps_failures(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, "0.4.0")
    runtime_store.save_bench(e["rig_id"], "prl", "srbminer", "pearlhash", None, None, "watchdog:exited")
    for _ in range(3):
        _report(client, e, "0.4.0")
    assert runtime_store.bench_for(e["rig_id"])[1] == {("prl", "srbminer")}


def test_client_update_retries_failures_of_all_groups(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _report(client, e, "0.4.0")
    runtime_store.save_bench(f"{e['rig_id']}#amd", "prl", "srbminer", "pearlhash", None, None, "watchdog:exited")
    runtime_store.save_bench("andere-id", "prl", "srbminer", "pearlhash", None, None, "watchdog:exited")
    _report(client, e, "0.4.1")
    assert runtime_store.bench_for(f"{e['rig_id']}#amd")[1] == set()
    assert runtime_store.bench_for("andere-id")[1] == {("prl", "srbminer")}      # fremder Rechner unberührt
