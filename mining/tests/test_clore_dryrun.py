"""Clore-Probelauf: Marktplatz lesen, Ertrag gegen Miete rechnen, Treffer speichern. Kein Geld."""
from __future__ import annotations

import pathlib
from datetime import datetime, timedelta, timezone

import pytest
from backend import catalog, clore, clore_store, store
from backend.profit import CoinQuote

P = "/api/modules/mining"


def _server(sid=1, gpu="2x NVIDIA GeForce RTX 3070", od=1.0, spot=0.5, rented=False, rel=0.99, mrl=72):
    return {"id": sid, "owner": 9, "mrl": mrl, "rented": rented, "reliability": rel,
            "specs": {"gpu": gpu, "cpu": "Pentium Gold"},
            "price": {"usd": {"on_demand_usd": od, "on_demand_btc": od * 1.2, "spot": 0},
                      "original_usd": {"bitcoin": {"on_demand": od * 1.2, "spot": spot * 1.2},
                                       "CLORE-Blockchain": {"on_demand": od, "spot": spot}}}}


@pytest.fixture
def quotes():
    """Jeder Coin bringt 1e-6 USD je H/s und Tag (PPS+), PRL doppelt so viel."""
    qs = [CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                    profit_per_hs_day=(2e-6 if c == "prl" else 1e-6), price_usd=1.0) for c in catalog.coins()]
    store.replace_quotes(qs)
    return {q.coin: q for q in qs}


# ---- Namen ----
@pytest.mark.parametrize("text, expected", [
    ("2x NVIDIA GeForce RTX 3070", (2, "nvidia-rtx-3070")),
    ("1x NVIDIA GeForce RTX 3060 Ti", (1, "nvidia-rtx-3060-ti")),
    ("8x Tesla V100SXM232GB", (8, "nvidia-v100")),
    ("1x Tesla V100SXM216GB", (1, "nvidia-v100")),
    ("4x Tesla T4", (4, "nvidia-t4")),
    ("10x NVIDIA GeForce RTX 5060 Ti", (10, "nvidia-rtx-5060-ti")),
    ("2x Mixed GPUs", None), ("", None), ("RTX 3070", None), ("0x NVIDIA GeForce RTX 3070", None),
])
def test_parse_gpu(text, expected):
    assert clore.parse_gpu(text) == expected


def test_5060ti_matches_16gb_reference():
    """Kryptex-Referenz heißt nvidia-rtx-5060-ti-16gb, Clore nennt die Speichergröße nicht."""
    assert clore.hashrates_for("nvidia-rtx-5060-ti")[1] == "reference"


# ---- Kosten ----
def test_costs_include_renter_fee():
    od, spot = clore.costs(_server(od=10.0, spot=6.0))
    assert od == pytest.approx(10.0 * 1.05)
    assert spot == pytest.approx(6.0 * 1.0125)


def test_costs_missing_prices():
    s = _server()
    s["price"] = {}
    assert clore.costs(s) == (None, None)


def test_spot_takes_lowest_currency():
    s = _server(od=10.0, spot=6.0)
    s["price"]["original_usd"]["bitcoin"]["spot"] = 5.0
    assert clore.costs(s)[1] == pytest.approx(5.0 * 1.0125)


# ---- Bewertung ----
def test_evaluate_profitable_server(quotes):
    """2× 3070 mit Referenz-Hashraten: Ertrag hoch genug gegen 1 $/Tag Miete."""
    r = clore.evaluate(_server(od=1.0, spot=0.5), quotes, prop_discount=0.0)
    assert r["status"] == "rated" and r["hit_od"] and r["hit_spot"]
    assert r["roi_od"] >= 0.12 and r["coin"] == "prl"
    assert r["source"] == "reference"


def test_evaluate_applies_conservative_factor(quotes):
    r = clore.evaluate(_server(od=1.0), quotes, prop_discount=0.0)
    raw = max(quotes[c].profit_per_hs_day * hs * 2 for c, hs in clore.hashrates_for("nvidia-rtx-3070")[0].items()
              if c in quotes)
    assert r["revenue"] == pytest.approx(raw * clore.SAFETY["reference"], rel=1e-6)


def test_below_12_percent_is_no_hit(quotes):
    r = clore.evaluate(_server(od=1.0), quotes, prop_discount=0.0)
    expensive = clore.evaluate(_server(od=r["revenue"] / 1.05 / 1.11), quotes, prop_discount=0.0)
    assert expensive["roi_od"] < 0.12 and not expensive["hit_od"]


def test_rented_and_unknown_skipped(quotes):
    assert clore.evaluate(_server(rented=True), quotes, prop_discount=0.0)["status"] == "rented"
    assert clore.evaluate(_server(gpu="2x Mixed GPUs"), quotes, prop_discount=0.0)["status"] == "gpu_unknown"
    assert clore.evaluate(_server(gpu="1x NVIDIA GeForce RTX 9999"), quotes,
                          prop_discount=0.0)["status"] == "no_benchmark"


def test_v100_without_own_measurement_uses_only_kryptex_values(quotes, monkeypatch):
    """Kryptex hat für V100 kein PRL/QTC → kein erfundener Wert, Bewertung nur mit vorhandenen Coins."""
    monkeypatch.setattr(clore, "_own", dict)
    hs, src = clore.hashrates_for("nvidia-v100")
    assert src == "reference" and "prl" not in hs and "qtc" not in hs


def test_own_measurement_wins(quotes, monkeypatch):
    monkeypatch.setattr(clore, "_own", lambda: {"nvidia-v100": {"prl": 1e6}})
    hs, src = clore.hashrates_for("nvidia-v100")
    assert src == "measured" and hs == {"prl": 1e6}
    r = clore.evaluate(_server(gpu="8x Tesla V100SXM232GB", od=1.0), quotes, prop_discount=0.0)
    assert r["revenue"] == pytest.approx(2e-6 * 1e6 * 8 * clore.SAFETY["measured"], rel=1e-6)


def test_prop_coin_gets_at_least_10_percent_discount(quotes):
    quotes["prl"] = CoinQuote(coin="prl", name="prl", algo="A", fee=0.01, fee_type="PROP",
                              profit_per_hs_day=2e-6, price_usd=1.0)
    r = clore.evaluate(_server(gpu="1x NVIDIA GeForce RTX 3070"), quotes, prop_discount=0.0)
    hs = clore.hashrates_for("nvidia-rtx-3070")[0]
    prl = 2e-6 * hs["prl"] * 0.9 * clore.SAFETY["reference"]
    other = max(1e-6 * v for c, v in hs.items() if c != "prl" and c in quotes) * clore.SAFETY["reference"]
    assert r["revenue"] == pytest.approx(max(prl, other), rel=1e-6)


def test_no_quotes_no_hit():
    r = clore.evaluate(_server(), {}, prop_discount=0.0)
    assert r["status"] == "no_benchmark" and not r.get("hit_od")


# ---- Lauf, Speicher, Aufräumen ----
def test_scan_stores_run_and_hits(quotes):
    servers = [_server(1, od=1.0), _server(2, od=1e12, spot=1e12), _server(3, rented=True), _server(4, gpu="2x Mixed GPUs")]
    run = clore.scan(servers, quotes, prop_discount=0.0)
    assert run == {"ok": True, "free": 3, "rated": 2, "hits": 1, "best_roi": pytest.approx(run["best_roi"])}
    s = clore_store.summary()
    assert s["last_run"]["hits"] == 1 and [h["server_id"] for h in s["hits_24h"]] == [1]


def test_failed_fetch_is_stored_as_not_ok(quotes):
    clore_store.save_run({"ok": False, "free": 0, "rated": 0, "hits": 0, "best_roi": None, "error": "timeout"}, [])
    assert clore_store.summary()["last_run"]["ok"] is False


def test_prune_after_14_days(quotes):
    old = datetime.now(timezone.utc) - timedelta(days=15)
    clore_store.save_run({"ok": True, "free": 1, "rated": 1, "hits": 1, "best_roi": 0.5},
                         [{"server_id": 7, "gpu": "nvidia-rtx-3070", "count": 1, "coin": "prl", "source": "reference",
                           "revenue": 2.0, "cost_od": 1.0, "cost_spot": None, "roi_od": 1.0, "roi_spot": None,
                           "reliability": 1.0, "mrl": 24}], now=old)
    clore_store._last_prune["at"] = datetime.min.replace(tzinfo=timezone.utc)   # Aufräumen fällig
    clore_store.save_run({"ok": True, "free": 0, "rated": 0, "hits": 0, "best_roi": None}, [])
    s = clore_store.summary()
    assert all(h["server_id"] != 7 for h in s["hits_24h"]) and clore_store.count_runs() == 1
    assert [d["day"] for d in s["days"]] == [datetime.now(timezone.utc).strftime("%Y-%m-%d")]


def test_prune_at_most_hourly(quotes):
    """Aufräumen kostet einen DELETE über die Tabelle – höchstens stündlich, nicht bei jedem Lauf."""
    clore_store._last_prune["at"] = datetime.now(timezone.utc)
    old = datetime.now(timezone.utc) - timedelta(days=15)
    clore_store.save_run({"ok": True, "free": 0, "rated": 0, "hits": 0, "best_roi": None}, [], now=old)
    clore_store.save_run({"ok": True, "free": 0, "rated": 0, "hits": 0, "best_roi": None}, [])
    assert clore_store.count_runs() == 2


def test_daily_summary(quotes):
    clore.scan([_server(1, od=1.0)], quotes, prop_discount=0.0)
    clore.scan([_server(1, od=1e12, spot=1e12)], quotes, prop_discount=0.0)
    (day,) = clore_store.summary()["days"]
    assert day["runs"] == 2 and day["runs_with_hits"] == 1 and day["top_gpu"] == "nvidia-rtx-3070"


# ---- Route, Schalter ----
def test_route_returns_summary(client, admin_headers, quotes):
    clore.scan([_server(1, od=1.0)], quotes, prop_discount=0.0)
    r = client.get(f"{P}/clore", headers=admin_headers)
    assert r.status_code == 200 and r.json()["last_run"]["hits"] == 1


def test_route_needs_login(client):
    assert client.get(f"{P}/clore").status_code in (401, 403)


async def test_job_respects_switch(quotes, monkeypatch):
    calls = []

    async def fake_fetch():
        calls.append(1)
        return [_server(1, od=1.0)]

    monkeypatch.setattr(clore, "fetch_marketplace", fake_fetch)
    store.update_config({"clore_dryrun": False})
    await clore.job()
    assert calls == []
    store.update_config({"clore_dryrun": True})
    await clore.job()
    assert calls == [1] and clore_store.summary()["last_run"]["hits"] == 1


async def test_job_fetch_error_stored(quotes, monkeypatch):
    async def boom():
        raise clore.CloreError("timeout")

    monkeypatch.setattr(clore, "fetch_marketplace", boom)
    store.update_config({"clore_dryrun": True})
    await clore.job()
    assert clore_store.summary()["last_run"]["ok"] is False


def test_no_write_endpoint_in_code():
    """Sicherheitsnetz: Der Probelauf enthält keinen schreibenden Clore-Aufruf und keinen Schlüssel."""
    src = pathlib.Path(clore.__file__).read_text()
    for forbidden in ("create_order", "cancel_order", "set_spot_price", "\"auth\"", ".post("):
        assert forbidden not in src


@pytest.mark.parametrize("rel, hit", [(0.99, True), (0.9, True), (0.89, False), (0.41, False), (None, False)])
def test_unreliable_server_is_no_hit(quotes, rel, hit):
    """Clore „reliability“ < 90 % (oft abgebrochen/offline) zählt nicht als Treffer – Rechnung bleibt sichtbar."""
    r = clore.evaluate(_server(od=1.0, spot=0.5, rel=rel), quotes, prop_discount=0.0)
    assert r["status"] == "rated" and r["roi_od"] >= 0.12
    assert r["hit_od"] is hit and r["hit_spot"] is hit
