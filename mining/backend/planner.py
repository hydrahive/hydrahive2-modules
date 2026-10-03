"""Bindeglied: Meldung eines Rigs → Messung speichern → entscheiden → Soll-Zustand.

Wird bei jeder Rig-Meldung (``/report``) aufgerufen. Die Energie-Steuerung
(power.py) liefert ``power_ok`` je Rig; sie wird einmal pro Meldung über alle
Rigs gerechnet, damit die Verteilung konsistent bleibt.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import catalog, power, runtime_store, store
from .decide import Assignment, decide

logger = logging.getLogger(__name__)
MAX_RIG_WATTS = 20_000   # bis ~20 Karten à 1 kW; alles darüber ist Unsinn
BENCH_SECONDS = 180


def _record_benchmark(rig: dict, state: dict) -> None:
    """Fertiges Benchmark-Ergebnis aus der Meldung übernehmen (nur passend zur Zuteilung)."""
    res = state.get("benchmark_result")
    if not isinstance(res, dict):
        return
    cur, _, _ = runtime_store.get_assignment(rig["id"])
    if not cur or cur.mode != "benchmark" or (res.get("coin"), res.get("miner")) != (cur.coin, cur.miner):
        return
    hr = res.get("hashrate")
    hr = float(hr) if isinstance(hr, (int, float)) and not isinstance(hr, bool) and 0 < hr < 1e18 else None
    w = res.get("watts")
    w = float(w) if isinstance(w, (int, float)) and not isinstance(w, bool) and 0 < w < MAX_RIG_WATTS else None
    runtime_store.save_bench(rig["id"], cur.coin, cur.miner, cur.algo, hr, w,
                             None if hr else str(res.get("error") or "no_hashrate"))


def desired_for(rig: dict, state: dict, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    _record_benchmark(rig, state)
    cfg = store.get_config()
    quotes = {q.coin: q for q in store.load_quotes()[0] if q.coin in catalog.coins()}
    bench, failed = runtime_store.bench_for(rig["id"])
    cur, since, _ = runtime_store.get_assignment(rig["id"])
    power_ok, power_changed, power_reason = power.allowed(rig, now=now)
    new = decide(rig=rig, cfg=cfg, quotes=quotes, bench=bench, failed=failed, current=cur,
                 current_since=since, now=now, power_ok=power_ok, power_reason=power_reason or "power_budget")
    runtime_store.set_assignment(rig["id"], new, cur, power_changed=power_changed)
    return to_wire(new, cfg, rig)


def to_wire(a: Assignment, cfg: dict, rig: dict) -> dict:
    """Soll-Zustand fürs Gerät: bei mine/benchmark nur der Auftrag (Namen), keine Befehle."""
    if a.mode == "stop" or not a.coin:
        return {"action": "stop", "reason": a.reason}
    try:
        job = catalog.job(a.coin, a.miner or "", a.algo or "", user=cfg["kryptex_user"],
                          worker=rig["name"], region=cfg.get("region", "eu"))
    except (ValueError, KeyError) as exc:
        logger.warning("Mining: Auftrag für %s ungültig: %s", rig.get("name"), exc)
        return {"action": "stop", "reason": f"invalid_job:{exc}"}
    out = {"action": a.mode, "reason": a.reason, "job": job}
    if a.mode == "benchmark":
        out["seconds"] = BENCH_SECONDS
    return out
