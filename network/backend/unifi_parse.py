"""Antworten der Dream Machine in flache Zeilen übersetzen (ohne Netz, gut testbar).

Quellen (gemessen 01.11.2026, Network 10.6.109): stat/health, v2 system-log/all, stat/report/archive.speedtest,
stat/report/{5minutes,hourly,daily}.site. Zeiten der Dream Machine sind Millisekunden, hier Sekunden.
"""
from __future__ import annotations

import re

_UNIT = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_PART = re.compile(r"^(\d+)([dhms])$")
# Ereignis der Dream Machine → eigene Art. Andere Kategorien (Clients, Sicherheit …) werden nicht übernommen.
KINDS = {
    "NETWORK_WAN_FAILED": "wan_failed",
    "NETWORK_WAN_RESTORED": "wan_restored",
    "NETWORK_WAN_FAILED_TEMPORARY": "wan_blip",
    "NETWORK_WAN_FAILED_MULTIPLE_TIMES": "wan_flapping",
    "ISP_PACKET_LOSS": "packet_loss",
    "ISP_HIGH_LATENCY": "high_latency",
}
SCALES = {"5min": "5minutes", "hour": "hourly", "day": "daily"}


def duration_s(text: str | None) -> int | None:
    """„8h 31m“ → 30660. Unlesbar → None."""
    if not text:
        return None
    total = 0
    for part in text.split():
        m = _PART.match(part)
        if not m:
            return None
        total += int(m.group(1)) * _UNIT[m.group(2)]
    return total


def _name(params: dict, key: str) -> str | None:
    v = params.get(key)
    return v.get("name") if isinstance(v, dict) else None


def health(raw: dict) -> dict:
    parts = {x.get("subsystem"): x for x in raw.get("data", []) if isinstance(x, dict)}
    wan, www = parts.get("wan", {}), parts.get("www", {})
    up = (wan.get("uptime_stats") or {}).get("WAN") or {}
    speed = None
    if www.get("speedtest_lastrun"):
        speed = {"down": www.get("xput_down"), "up": www.get("xput_up"), "ping": www.get("speedtest_ping"),
                 "at": www.get("speedtest_lastrun")}
    return {"wan_status": wan.get("status"), "isp": wan.get("isp_name"), "availability": up.get("availability"),
            "latency_ms": www.get("latency"), "drops": www.get("drops"), "speedtest": speed}


def events(raw: dict) -> list[dict]:
    out = []
    for e in raw.get("data", []):
        kind = KINDS.get(e.get("event", ""))
        if not kind or e.get("category") != "INTERNET_AND_WAN":
            continue
        p = e.get("parameters") or {}
        out.append({"event_id": e["id"], "source": "udm", "ts": int(e["timestamp"]) // 1000, "kind": kind,
                    "wan": _name(p, "WAN_NAME"), "duration_s": duration_s(_name(p, "DURATION")),
                    "detail": _name(p, "LATENCY")})
    return out


def speedtests(raw: dict) -> list[dict]:
    return [{"source": "udm", "ts": int(x["rundate"]), "down_mbit": x.get("xput_download"),
             "up_mbit": x.get("xput_upload"), "ping_ms": x.get("latency"),
             "server": (x.get("server") or {}).get("city")}
            for x in raw.get("data", []) if x.get("rundate")]


def series(scale: str, raw: dict) -> list[dict]:
    if scale not in SCALES:
        raise ValueError(scale)
    return [{"scale": scale, "ts": int(r["time"]) // 1000, "latency_avg": r.get("latency_avg"),
             "latency_min": r.get("latency_min"), "latency_max": r.get("latency_max"),
             "rx_bytes": r.get("wan-rx_bytes"), "tx_bytes": r.get("wan-tx_bytes")}
            for r in raw.get("data", []) if r.get("time")]
