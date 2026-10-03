"""Entscheider (reine Funktionen) + Katalog."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend import catalog
from backend.decide import Assignment, decide, pending_benchmarks
from backend.profit import CoinQuote

NOW = datetime(2026, 10, 3, 16, 0, tzinfo=timezone.utc)
RIG = {"status": "active", "enabled": 1, "gpu_vendor": "nvidia"}
CFG = {"kryptex_user": "krxTEST", "switch_threshold": 0.05, "min_runtime_min": 15, "prop_discount": 0.0}


def _q(coin, profit=1e-6, price=1.0, fee_type="PPS+"):
    return CoinQuote(coin=coin, name=coin, algo="A", fee=0.01, fee_type=fee_type, profit_per_hs_day=profit, price_usd=price)


def _all_bench(value=1e6, vendor="nvidia"):
    return {(c, m): value for c in catalog.coins() for m, _ in catalog.options(c, vendor)}


def _run(**kw):
    args = {"rig": RIG, "cfg": CFG, "quotes": {c: _q(c) for c in catalog.coins()}, "bench": _all_bench(), "failed": set(),
            "current": None, "current_since": None, "now": NOW}
    args.update(kw)
    return decide(**args)


# ---- Katalog ----
def test_catalog_all_coins_have_nvidia_option_and_valid_miners():
    for coin in catalog.coins():
        opts = catalog.options(coin, "nvidia")
        assert opts, coin
        for miner, _ in opts:
            assert miner in catalog.miners()
            assert "nvidia" in catalog.miners()[miner]["vendors"]
        for miner, _ in catalog.options(coin, "amd"):
            assert "amd" in catalog.miners()[miner]["vendors"], (coin, miner)   # Rigel ist NVIDIA-only


def test_catalog_hashes_and_urls():
    for name, m in catalog.miners().items():
        assert len(m["sha256"]) == 64 and int(m["sha256"], 16) >= 0, name
        assert m["url"].startswith("https://github.com/"), name


def test_job_contains_only_names():
    j = catalog.job("rvn", "rigel", "kawpow", user="krxXJK8JJW", worker="till-wks", region="eu")
    assert j == {"coin": "rvn", "miner": "rigel", "algo": "kawpow", "user": "krxXJK8JJW",
                 "worker": "till-wks", "region": "eu", "version": "1.23.2"}


def test_catalog_families_consistent():
    for coin in catalog.coins():
        assert catalog.family(coin)


@pytest.mark.parametrize("kw", [{"user": "a b"}, {"user": ""}, {"worker": "Rig 1"}, {"worker": "-x"},
                                {"user": "x;rm -rf /"}, {"region": "mars"}])
def test_job_rejects_bad_input(kw):
    args = {"user": "krxA", "worker": "r1", "region": "eu"}
    args.update(kw)
    with pytest.raises(ValueError):
        catalog.job("rvn", "rigel", "kawpow", **args)


def test_job_rejects_combination_outside_catalog():
    with pytest.raises(ValueError):
        catalog.job("prl", "rigel", "pearlhash", user="krxA", worker="r1", region="eu")


# ---- Entscheider ----
@pytest.mark.parametrize("rig,cfg,reason", [
    ({**RIG, "status": "pending"}, CFG, "awaiting_approval"),
    ({**RIG, "enabled": 0}, CFG, "disabled"),
    (RIG, {**CFG, "kryptex_user": ""}, "no_kryptex_user"),
    ({**RIG, "gpu_vendor": "none"}, CFG, "no_supported_gpu"),
])
def test_stop_reasons(rig, cfg, reason):
    assert _run(rig=rig, cfg=cfg) == Assignment("stop", reason=reason)


def test_power_budget_stops():
    assert _run(power_ok=False).reason == "power_budget"


def test_benchmarks_first_until_all_measured():
    a = _run(bench={})
    assert a.mode == "benchmark" and (a.coin, a.miner) == pending_benchmarks("nvidia", set(), {c: _q(c) for c in catalog.coins()})[0][:2]


def test_failed_benchmarks_are_skipped():
    allpairs = set(_all_bench())
    a = _run(bench={("rvn", "rigel"): 1e6}, failed=allpairs - {("rvn", "rigel")})
    assert a.mode == "mine" and (a.coin, a.miner) == ("rvn", "rigel")


def test_benchmark_only_for_coins_kryptex_offers():
    a = _run(bench={}, quotes={"rvn": _q("rvn")})
    assert a.coin == "rvn"


def test_picks_highest_earning():
    bench = _all_bench(1e6)
    bench[("prl", "srbminer")] = 5e6
    a = _run(bench=bench)
    assert (a.mode, a.coin, a.miner) == ("mine", "prl", "srbminer")


def test_amd_never_gets_rigel():
    a = _run(rig={**RIG, "gpu_vendor": "amd"}, bench=_all_bench(1e6, "amd"))
    assert a.miner != "rigel"


def test_keeps_current_below_threshold():
    bench = _all_bench(1e6)
    bench[("prl", "srbminer")] = 1.04e6                    # nur 4 % besser
    cur = Assignment("mine", "rvn", "rigel", "kawpow")
    a = _run(bench=bench, current=cur, current_since=NOW - timedelta(hours=1))
    assert (a.coin, a.reason) == ("rvn", "keep (below_threshold)")


def test_switches_above_threshold_after_min_runtime():
    bench = _all_bench(1e6)
    bench[("prl", "srbminer")] = 1.06e6
    cur = Assignment("mine", "rvn", "rigel", "kawpow")
    assert _run(bench=bench, current=cur, current_since=NOW - timedelta(minutes=16)).coin == "prl"


def test_keeps_current_before_min_runtime_even_if_much_better():
    bench = _all_bench(1e6)
    bench[("prl", "srbminer")] = 9e6
    cur = Assignment("mine", "rvn", "rigel", "kawpow")
    a = _run(bench=bench, current=cur, current_since=NOW - timedelta(minutes=14))
    assert (a.coin, a.reason) == ("rvn", "keep (too_soon)")


def test_switches_immediately_when_current_coin_disappears():
    quotes = {c: _q(c) for c in catalog.coins() if c != "rvn"}
    cur = Assignment("mine", "rvn", "rigel", "kawpow")
    a = _run(quotes=quotes, current=cur, current_since=NOW - timedelta(minutes=1))
    assert a.coin != "rvn" and a.mode == "mine"


def test_no_option_when_nothing_has_price():
    a = _run(quotes={c: _q(c, price=None) for c in catalog.coins()})
    assert a == Assignment("stop", reason="no_profitable_option")


def test_prop_discount_changes_choice():
    bench = _all_bench(1e6)
    bench[("qtc", "x")] = 0
    quotes = {c: _q(c) for c in catalog.coins()}
    quotes["xel"] = _q("xel", profit=1.1e-6, fee_type="PROP")
    assert _run(quotes=quotes, bench=bench).coin == "xel"
    assert _run(quotes=quotes, bench=bench, cfg={**CFG, "prop_discount": 0.2}).coin != "xel"
