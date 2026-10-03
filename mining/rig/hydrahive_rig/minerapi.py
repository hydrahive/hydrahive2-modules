"""Status der Miner über ihre lokale API (nur 127.0.0.1) lesen.

Formate am 03.10.2026 echt erhoben (tills-master-wks, RTX 5060 Ti):
- rigel:    {"hashrate": {"kawpow": 21213765.1}, "solution_stat": {"kawpow": {"accepted": 1, …}}, …}
- srbminer: {"algorithms": [{"hashrate": {"gpu": {"total": 8.99e13}}, "shares": {"accepted": 1, …}}]}
- lolminer: {"Algorithms": [{"Total_Performance": 45.5, "Performance_Factor": 1e6,
             "Total_Accepted": 1, "Total_Rejected": 0}], "Workers": [{"Power": 138.7, …}]}
Ergebnis immer: {"hashrate": H/s | None, "accepted": int, "rejected": int, "watts": float | None}
"""
from __future__ import annotations

import json
import urllib.request


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def parse(kind: str, d: dict) -> dict:
    out = {"hashrate": None, "accepted": 0, "rejected": 0, "watts": None}
    if kind == "rigel":
        hr = d.get("hashrate") or {}
        out["hashrate"] = _num(sum(v for v in hr.values() if _num(v))) if isinstance(hr, dict) and hr else None
        for s in (d.get("solution_stat") or {}).values():
            out["accepted"] += int(s.get("accepted") or 0)
            out["rejected"] += int(s.get("rejected") or 0) + int(s.get("invalid") or 0)
        dev = (d.get("devices") or [{}])[0]
        out["watts"] = _num(dev.get("power_usage"))
    elif kind == "srbminer":
        a = (d.get("algorithms") or [{}])[0]
        out["hashrate"] = _num(((a.get("hashrate") or {}).get("gpu") or {}).get("total"))
        sh = a.get("shares") or {}
        out["accepted"], out["rejected"] = int(sh.get("accepted") or 0), int(sh.get("rejected") or 0)
    elif kind == "lolminer":
        a = (d.get("Algorithms") or [{}])[0]
        perf, fac = _num(a.get("Total_Performance")), _num(a.get("Performance_Factor")) or 1.0
        out["hashrate"] = perf * fac if perf is not None else None
        out["accepted"], out["rejected"] = int(a.get("Total_Accepted") or 0), int(a.get("Total_Rejected") or 0)
        out["watts"] = _num((d.get("Workers") or [{}])[0].get("Power"))
    if out["hashrate"] is not None and out["hashrate"] <= 0:
        out["hashrate"] = None
    return out


def read(kind: str, port: int, timeout: float = 3.0) -> dict | None:
    """None = API (noch) nicht erreichbar."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=timeout) as r:  # fest lokal (127.0.0.1)
            return parse(kind, json.loads(r.read(1 << 20)))
    except (OSError, ValueError):
        return None
