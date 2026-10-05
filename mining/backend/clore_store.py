"""Speicher für den Clore-Probelauf: Läufe und Treffer, 14 Tage."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

KEEP_DAYS = 14
_HIT_FIELDS = ("server_id", "gpu", "count", "coin", "source", "revenue", "cost_od", "cost_spot",
               "roi_od", "roi_spot", "reliability", "mrl")
_last_prune = {"at": datetime.min.replace(tzinfo=timezone.utc)}


def save_run(run: dict, hits: list[dict], *, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    ts = now.isoformat(timespec="seconds")
    with db() as c:
        cur = c.execute(
            "INSERT INTO module_mining_clore_runs (ts, ok, free, rated, hits, best_roi, error) VALUES (?,?,?,?,?,?,?)",
            (ts, 1 if run.get("ok") else 0, run.get("free", 0), run.get("rated", 0), run.get("hits", 0),
             run.get("best_roi"), (run.get("error") or "")[:200] or None))
        run_id = cur.lastrowid
        for h in hits:
            c.execute(
                "INSERT INTO module_mining_clore_hits (run_id, ts, data) VALUES (?,?,?)",
                (run_id, ts, json.dumps({k: h.get(k) for k in _HIT_FIELDS}, separators=(",", ":"))))
        real_now = datetime.now(timezone.utc)
        if not timedelta(0) <= real_now - _last_prune["at"] < timedelta(hours=1):
            cutoff = (real_now - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
            c.execute("DELETE FROM module_mining_clore_hits WHERE ts < ?", (cutoff,))
            c.execute("DELETE FROM module_mining_clore_runs WHERE ts < ?", (cutoff,))
            _last_prune["at"] = real_now
    return run_id


def count_runs() -> int:
    with db() as c:
        return c.execute("SELECT COUNT(*) FROM module_mining_clore_runs").fetchone()[0]


def _hit_row(r) -> dict:
    return {"ts": r["ts"], **json.loads(r["data"])}


def summary() -> dict:
    """Letzter Lauf, Treffer der letzten 24 h (bester zuerst), Zusammenfassung je Tag."""
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    with db() as c:
        last = c.execute("SELECT * FROM module_mining_clore_runs ORDER BY id DESC LIMIT 1").fetchone()
        hits = [_hit_row(r) for r in c.execute(
            "SELECT ts, data FROM module_mining_clore_hits WHERE ts >= ? ORDER BY id DESC LIMIT 500", (since,))]
        runs = c.execute("SELECT substr(ts,1,10) AS day, hits, best_roi FROM module_mining_clore_runs "
                         "WHERE ok = 1 ORDER BY ts").fetchall()
        all_hits = c.execute("SELECT substr(ts,1,10) AS day, data FROM module_mining_clore_hits").fetchall()
    gpus: dict[str, Counter] = {}
    for r in all_hits:
        gpus.setdefault(r["day"], Counter())[json.loads(r["data"]).get("gpu")] += 1
    days: dict[str, dict] = {}
    for r in runs:
        d = days.setdefault(r["day"], {"day": r["day"], "runs": 0, "runs_with_hits": 0, "best_roi": None})
        d["runs"] += 1
        d["runs_with_hits"] += 1 if r["hits"] else 0
        if r["best_roi"] is not None and (d["best_roi"] is None or r["best_roi"] > d["best_roi"]):
            d["best_roi"] = r["best_roi"]
    for d in days.values():
        top = gpus.get(d["day"])
        d["top_gpu"] = top.most_common(1)[0][0] if top else None
    hits.sort(key=lambda h: max(h.get("roi_od") or -9, h.get("roi_spot") or -9), reverse=True)
    return {"last_run": (dict(last) | {"ok": bool(last["ok"])}) if last else None,
            "hits_24h": hits[:100], "days": sorted(days.values(), key=lambda d: d["day"])}
