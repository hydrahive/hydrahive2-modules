"""Bindeglied: Meldung eines Rigs → Messung speichern → entscheiden → Soll-Zustand.

Wird bei jeder Rig-Meldung (``/report``) aufgerufen. Die Energie-Steuerung
(power.py) liefert ``power_ok`` je Rig; sie wird einmal pro Meldung über alle
Rigs gerechnet, damit die Verteilung konsistent bleibt.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from . import catalog, groups, power, runtime_store, store
from .decide import Assignment, decide

logger = logging.getLogger(__name__)
MAX_RIG_WATTS = 20_000   # bis ~20 Karten à 1 kW; alles darüber ist Unsinn
BENCH_SECONDS = 180


def _record_benchmark(key: str, state: dict) -> None:
    """Fertiges Benchmark-Ergebnis aus der Meldung übernehmen (nur passend zur Zuteilung der Gruppe)."""
    res = state.get("benchmark_result")
    if not isinstance(res, dict):
        return
    cur, _, _ = runtime_store.get_assignment(key)
    if not cur or cur.mode != "benchmark" or (res.get("coin"), res.get("miner")) != (cur.coin, cur.miner):
        return
    hr = res.get("hashrate")
    hr = float(hr) if isinstance(hr, (int, float)) and not isinstance(hr, bool) and 0 < hr < 1e18 else None
    w = res.get("watts")
    w = float(w) if isinstance(w, (int, float)) and not isinstance(w, bool) and 0 < w < MAX_RIG_WATTS else None
    runtime_store.save_bench(key, cur.coin, cur.miner, cur.algo, hr, w,
                             None if hr else str(res.get("error") or "no_hashrate"))


def _decide_group(rig: dict, vendor: str, key: str, gstate: dict, mem: int | None, *, cfg: dict, quotes: dict,
                  now: datetime, power: tuple[bool, bool, str]) -> Assignment:
    _record_benchmark(key, gstate)
    bench, failed = runtime_store.bench_for(key)
    cur, since, _ = runtime_store.get_assignment(key)
    power_ok, power_changed, power_reason = power
    new = decide(rig={**rig, "gpu_vendor": vendor, "gpu_mem_mb": mem}, cfg=cfg, quotes=quotes, bench=bench,
                 failed=failed, current=cur, current_since=since, now=now, power_ok=power_ok,
                 power_reason=power_reason or "power_budget")
    runtime_store.set_assignment(key, new, cur, power_changed=power_changed)
    return new


def desired_for(rig: dict, state: dict, *, now: datetime | None = None) -> dict:
    """Soll-Zustand je Hersteller-Gruppe; flach (wie bisher) zusätzlich für Rechner mit einer Gruppe."""
    now = now or datetime.now(timezone.utc)
    cfg = store.get_config()
    quotes = {q.coin: q for q in store.load_quotes()[0] if q.coin in catalog.coins()}
    keys = groups.keys(rig, state)
    if not keys:   # keine unterstützte Karte → wie bisher über decide() begründen
        new = decide(rig=rig, cfg=cfg, quotes=quotes, bench={}, failed=set(), current=None, current_since=None,
                     now=now)
        runtime_store.set_assignment(rig["id"], new, runtime_store.get_assignment(rig["id"])[0], power_changed=False)
        return {**to_wire(new, cfg, rig), "groups": {}}
    mixed = len(keys) > 1
    pw = power.allowed(rig, now=now, state_key=next(iter(keys.values())))
    out: dict = {"groups": {}}
    for vendor, key in keys.items():
        new = _decide_group(rig, vendor, key, groups.group_state(state, vendor, mixed),
                            groups.mem_mb(rig, state, vendor, mixed), cfg=cfg, quotes=quotes, now=now, power=pw)
        out["groups"][vendor] = to_wire(new, cfg, rig)
    if not mixed:
        out.update(out["groups"][next(iter(keys))])     # alte Clients lesen das flache Soll
    else:
        out.update({"action": "stop", "reason": "mixed_rig_old_client"})
    return out


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
