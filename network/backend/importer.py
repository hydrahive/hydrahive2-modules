"""Sicherung der Dream Machine übernehmen (JSON oder .json.gz, Format der Beweis-Sicherung vom 01.11.2026)."""
from __future__ import annotations

import gzip
import json

from . import store, unifi_parse
from .errors import NetError

_SERIES = {"site_5min_24h": "5min", "site_hourly_7d": "hour", "site_daily_90d": "day"}


def _part(snap: dict, key: str):
    p = snap.get(key)
    return p.get("data") if isinstance(p, dict) and p.get("status") == 200 else None


def load(raw: bytes) -> dict:
    try:
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        snap = json.loads(raw.decode("utf-8"))
    except (OSError, EOFError, ValueError):
        raise NetError("network_import_invalid") from None
    if not isinstance(snap, dict) or not any(k in snap for k in ("system_log_90d", "speedtest_90d", *_SERIES)):
        raise NetError("network_import_invalid")
    out = {"events": 0, "speedtests": 0, "5min": 0, "hour": 0, "day": 0}
    logs = _part(snap, "system_log_90d")
    if isinstance(logs, list):
        out["events"] = store.add_events(unifi_parse.events({"data": logs}))
    st = _part(snap, "speedtest_90d")
    if isinstance(st, dict):
        out["speedtests"] = store.add_speedtests(unifi_parse.speedtests(st))
    for key, scale in _SERIES.items():
        d = _part(snap, key)
        if isinstance(d, dict):
            rows = unifi_parse.series(scale, d)
            store.put_series(rows)
            out[scale] = len(rows)
    return out
