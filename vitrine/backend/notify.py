"""Fehler-Einblendungen + Hydra-Status für die Vitrine (Job alle 30 s im HydraHive-Prozess).

Liest neue Einträge aus errors_log (nur error/critical), blendet pro Quelle höchstens alle 10 min eine Karte
ein und schreibt <daten>/hydra.json (laufende Agenten, Fehler der letzten Stunde) für die Status-Leiste.
Der Lese-Zeiger liegt in <daten>/notify.json, damit nach einem Neustart nichts doppelt erscheint.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import time
from pathlib import Path

from hydrahive.settings import settings
from renderer import inbox

logger = logging.getLogger(__name__)

SHOW_SEVERITIES = ("error", "critical")
SOURCE_COOLDOWN = 600.0
MAX_PER_HOUR = 6
_last_shown: dict[str, float] = {}


def data_dir() -> Path:
    return settings.data_dir / "vitrine"


def _iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="milliseconds")


def _secrets(user: str | None, agent: str | None) -> set[str]:
    from hydrahive.credentials.redaction import egress_secrets
    return egress_secrets(user, agent)


def _errors_since(since: str) -> list[dict]:
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute("SELECT created_at, source, severity, error_message FROM errors_log "
                            "WHERE created_at > ? ORDER BY created_at LIMIT 500", (since,)).fetchall()
    return [dict(r) for r in rows]


def _active_agents() -> int:
    from hydrahive.runner.concurrency import active_count
    return active_count()


def safe_text(text: str, user: str | None = None, agent: str | None = None) -> str:
    from hydrahive.credentials.redaction import scrub
    return scrub(str(text or ""), _secrets(user, agent))


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj))
    tmp.replace(path)


def _load_marker(d: Path, now: float) -> tuple[str, dict, list[float]]:
    try:
        raw = json.loads((d / "notify.json").read_text())
        return (str(raw["cursor"]), {k: float(v) for k, v in raw.get("shown", {}).items()},
                [float(t) for t in raw.get("posted", [])])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return _iso(now), {}, []               # erster Start: Altes nicht nachholen


def tick(*, now: float | None = None) -> None:
    now = time.time() if now is None else now
    d = data_dir()
    cursor, shown, posted = _load_marker(d, now)
    shown.update(_last_shown)
    posted = [t for t in posted if now - t < 3600]
    rows = _errors_since(_iso(now - 3600))
    errors = [r for r in rows if r.get("severity") in SHOW_SEVERITIES]
    latest: dict[str, dict] = {}
    for r in errors:
        if r["created_at"] > cursor:
            latest[r.get("source") or "?"] = r            # pro Quelle das Neueste
    for src, r in latest.items():
        if now - shown.get(src, -1e12) < SOURCE_COOLDOWN or len(posted) >= MAX_PER_HOUR:
            continue
        try:
            inbox.post(d, safe_text(r.get("error_message") or "Fehler") or "Fehler", kind="error",
                       title=f"Fehler: {src}", source="errors_log")
            shown[src] = now
            posted.append(now)
        except inbox.InboxError as e:
            logger.debug("Vitrine-Fehlerkarte verworfen: %s", e)
    if rows:
        cursor = max(cursor, max(r["created_at"] for r in rows))
    _last_shown.clear()
    _last_shown.update({k: v for k, v in shown.items() if now - v < SOURCE_COOLDOWN})
    _write_json(d / "notify.json", {"cursor": cursor, "shown": _last_shown, "posted": posted})
    _write_json(d / "hydra.json", {"agents": _active_agents(), "errors_last_hour": len(errors), "updated": now})


async def job() -> None:
    await asyncio.to_thread(tick)
