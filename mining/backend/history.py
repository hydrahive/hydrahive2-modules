"""Verlauf für das Diagramm: eine Probe pro Rig und Minute, 7 Tage aufbewahrt.

Der Ertrag wird beim Speichern mit dem damaligen Kurs berechnet — das Diagramm
zeigt, was zu dem Zeitpunkt verdient wurde, nicht die alte Hashrate zum
heutigen Kurs. Rohe Hashrate wird nicht gezeigt (Einheiten je Coin um 10⁶
verschieden); stattdessen % der eigenen Benchmark-Messung.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

from . import runtime_store, store
from .profit import usd_per_day

KEEP_DAYS = 7
MAX_CARDS = 64
_PRUNE_EVERY = timedelta(hours=1)
_last_prune: dict[str, datetime] = {"at": datetime.min.replace(tzinfo=timezone.utc)}


def _num(v, lo: float, hi: float) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if lo <= v <= hi else None


def _cards(state: dict) -> list[dict]:
    raw = state.get("gpus") if isinstance(state.get("gpus"), list) else []
    return [{"temp_c": _num(g.get("temp_c"), -20, 150) if isinstance(g, dict) else None,
             "power_w": _num(g.get("power_w"), 0, 2000) if isinstance(g, dict) else None,
             "util_pct": _num(g.get("util_pct"), 0, 100) if isinstance(g, dict) else None}
            for g in raw[:MAX_CARDS]]


def _sample(rig_id: str, state: dict) -> dict:
    cur, _, _ = runtime_store.get_assignment(rig_id)
    mode = cur.mode if cur else "stop"
    out = {"mode": mode, "coin": cur.coin if cur else None, "miner": cur.miner if cur else None,
           "usd_day": None, "pct": None, "cards": _cards(state)}
    hr = _num(state.get("hashrate"), 1e-9, 1e18)
    if mode != "mine" or not cur or not cur.coin or hr is None:
        return out
    quote = next((q for q in store.load_quotes()[0] if q.coin == cur.coin), None)
    if quote is not None:
        out["usd_day"] = usd_per_day(quote, hr, prop_discount=store.get_config().get("prop_discount", 0.0))
    bench, _ = runtime_store.bench_for(rig_id)
    ref = bench.get((cur.coin, cur.miner or ""))
    if ref:
        out["pct"] = round(hr / ref * 100, 1)
    return out


def record(rig: dict, state: dict, *, now: datetime | None = None) -> None:
    """Probe speichern; gleiche Minute → nichts tun (Rig meldet alle 30 s)."""
    now = (now or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    data = json.dumps(_sample(rig["id"], state if isinstance(state, dict) else {}), separators=(",", ":"))
    with db() as c:
        c.execute("INSERT OR IGNORE INTO module_mining_samples (rig_id, ts, data) VALUES (?, ?, ?)",
                  (rig["id"], now.isoformat(), data))
        # höchstens stündlich; Zeitsprung zurück (Tests, Uhrkorrektur) → sofort erneut prüfen
        if not timedelta(0) <= now - _last_prune["at"] < _PRUNE_EVERY:
            c.execute("DELETE FROM module_mining_samples WHERE ts < ?",
                      ((now - timedelta(days=KEEP_DAYS)).isoformat(),))
            _last_prune["at"] = now


def points(rig_id: str, *, since: datetime) -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT ts, data FROM module_mining_samples WHERE rig_id = ? AND ts >= ? ORDER BY ts",
                         (rig_id, since.isoformat())).fetchall()
    return [{"ts": r["ts"], **json.loads(r["data"])} for r in rows]


def _mean(values: list) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 4) if vals else None


def downsample(pts: list[dict], max_points: int) -> list[dict]:
    """Höchstens ``max_points`` Punkte: Mittelwert je Fenster, Coin/Modus = letzter im Fenster."""
    if len(pts) <= max_points:
        return pts
    size = len(pts) / max_points
    out = []
    for i in range(max_points):
        win = pts[int(i * size):int((i + 1) * size)] or pts[int(i * size):int(i * size) + 1]
        last = win[-1]
        n_cards = max((len(p["cards"]) for p in win), default=0)
        cards = [{k: _mean([p["cards"][j][k] for p in win if j < len(p["cards"])])
                  for k in ("temp_c", "power_w", "util_pct")} for j in range(n_cards)]
        out.append({"ts": last["ts"], "mode": last["mode"], "coin": last["coin"], "miner": last.get("miner"),
                    "usd_day": _mean([p["usd_day"] for p in win]), "pct": _mean([p["pct"] for p in win]),
                    "cards": cards})
    return out
