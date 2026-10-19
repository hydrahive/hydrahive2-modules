"""Datenquellen der Statuszentrale (S2). Je Bereich eine Funktion; fehlt eine Tabelle oder scheitert etwas, liefert der
Bereich None und der Rest der Seite bleibt (SPEC-STATUSZENTRALE.md, S2). Die Datenbank kommt als `connect` herein
(Standard: die HydraHive-Datenbank), damit die Quellen ohne Kern testbar sind. Schwärzen und Kürzen macht dash_data.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)
TITLE_MAX, ERROR_MAX, TOP_TASKS = 80, 140, 5
_PRIO = "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"


def _hh_db():
    from hydrahive.db.connection import db
    return db()


def _iso(t: float, spec: str = "milliseconds") -> str:
    """Gleiches Format wie die Quelle: errors_log mit Millisekunden (now_iso), Mining-Proben auf Sekunden."""
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec=spec)


def _cut(s, n: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _has_table(c, name: str) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def safe(fn: Callable):
    try:
        return fn()
    except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as e:
        log.warning("Statuszentrale: Quelle fehlgeschlagen: %s", e)
        return None


def message(data_dir: Path) -> dict | None:
    from renderer import inbox
    msgs = inbox.visible(data_dir)
    if not msgs:
        return None
    m = max(msgs, key=lambda x: x.get("created", 0))
    return {"title": m.get("title") or "", "text": m.get("text") or "", "kind": m.get("kind") or "info"}


def hydra(*, connect=_hh_db, active: Callable[[], int] | None = None, service: Callable[[], str] | None = None,
          now: float | None = None) -> dict:
    now = time.time() if now is None else now
    if active is None:
        from hydrahive.runner.concurrency import active_count as active
    if service is None:
        from renderer.sysinfo import hydra_state as service
    errors: dict[str, dict] = {}
    with connect() as c:
        if _has_table(c, "errors_log"):
            rows = c.execute("SELECT created_at, source, error_message FROM errors_log WHERE created_at > ? AND severity IN "
                             "('error','critical') ORDER BY created_at LIMIT 500", (_iso(now - 3600),)).fetchall()
            for r in rows:
                e = errors.setdefault(r["source"] or "?", {"source": r["source"] or "?", "count": 0, "last": ""})
                e["count"] += 1
                e["last"] = _cut(r["error_message"], ERROR_MAX)
    errs = sorted(errors.values(), key=lambda e: -e["count"])
    return {"service": service(), "agents": int(active()), "errors_last_hour": sum(e["count"] for e in errs),
            "errors": errs[:5]}


def tasks(username: str, *, connect=_hh_db) -> dict | None:
    with connect() as c:
        if not _has_table(c, "module_tasks"):
            return None
        counts = dict(c.execute("SELECT status, COUNT(*) FROM module_tasks WHERE username=? AND status IN "
                                "('open','in_progress') GROUP BY status", (username,)).fetchall())
        top = c.execute(f"SELECT title, priority, status FROM module_tasks WHERE username=? AND status IN "
                        f"('open','in_progress') ORDER BY {_PRIO}, created_at ASC LIMIT ?", (username, TOP_TASKS)).fetchall()
    return {"open": int(counts.get("open", 0)), "in_progress": int(counts.get("in_progress", 0)),
            "top": [{"title": _cut(r["title"], TITLE_MAX), "priority": r["priority"], "status": r["status"]} for r in top]}


def _status() -> dict:
    from renderer import sysinfo
    return {"hydra": sysinfo.hydra_state(), "load": os.getloadavg()[0], "ram": sysinfo.ram_percent(), "gpu": sysinfo.gpu_temp()}


def _disk() -> tuple[int, int]:
    u = shutil.disk_usage("/")
    return 100, round(100 * u.free / u.total)


def _uptime() -> float:
    return float(Path("/proc/uptime").read_text().split()[0])


def machine(*, status=_status, disk=_disk, uptime=_uptime) -> dict:
    s = status()
    return {"load": round(float(s["load"]), 2), "ram": s.get("ram"), "gpu": s.get("gpu"), "disk_free_pct": disk()[1],
            "uptime_h": int(uptime() // 3600)}


def mining(*, connect=_hh_db, now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    with connect() as c:
        if not all(_has_table(c, t) for t in ("module_mining_rigs", "module_mining_samples", "module_mining_config")):
            return None
        row = c.execute("SELECT value FROM module_mining_config WHERE key='_usd_per_eur'").fetchone()
        rate = float(json.loads(row["value"])) if row else None
        rigs, total = [], 0.0
        for r in c.execute("SELECT id, name, enabled FROM module_mining_rigs WHERE status != 'revoked' ORDER BY name"):
            s = c.execute("SELECT data FROM module_mining_samples WHERE rig_id=? AND ts >= ? ORDER BY ts DESC LIMIT 1",
                          (r["id"], _iso(now - 900, "seconds"))).fetchone()
            usd = json.loads(s["data"]).get("usd_day") if s else None
            total += usd or 0.0
            rigs.append({"name": _cut(r["name"], 40), "mining": bool(r["enabled"]) and usd is not None})
    return {"eur_day": total / rate if rate else None, "rigs": rigs}
