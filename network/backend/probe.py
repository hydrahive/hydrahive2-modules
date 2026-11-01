"""Eigene Messung: ping mit fester Argumentliste (keine Shell, nur IP-Adressen als Ziel)."""
from __future__ import annotations

import asyncio
import ipaddress
import re
import statistics

_LOSS = re.compile(r"(\d+(?:\.\d+)?)% packet loss")
_RTT = re.compile(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms")
_EMPTY = {"loss": None, "min": None, "avg": None, "max": None, "mdev": None}


def valid_target(t: str) -> bool:
    try:
        ipaddress.ip_address(t)
        return True
    except ValueError:
        return False


def parse_ping(out: str) -> dict:
    m = _LOSS.search(out)
    r = _RTT.search(out)
    loss = float(m.group(1)) if m else 100.0
    if not r:
        return {"loss": loss, "min": None, "avg": None, "max": None, "mdev": None}
    mn, avg, mx, md = (float(x) for x in r.groups())
    return {"loss": loss, "min": mn, "avg": avg, "max": mx, "mdev": md}


async def _run(args: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT)
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
    return out.decode(errors="replace")


async def ping(target: str, count: int = 5) -> dict:
    if not valid_target(target):
        return dict(_EMPTY)
    try:
        out = await _run(["ping", "-n", "-q", "-c", str(count), "-i", "0.2", "-W", "1", target])
    except (OSError, asyncio.TimeoutError):
        return dict(_EMPTY)
    return parse_ping(out)


def combine(results: list[dict]) -> dict:
    """Internet aus mehreren Zielen: erreichbar, wenn mindestens eins antwortet. Werte nur von antwortenden Zielen."""
    known = [r for r in results if r.get("loss") is not None]
    if not known:
        return dict(_EMPTY)
    alive = [r for r in known if r["loss"] < 100.0]
    if not alive:
        return {"loss": 100.0, "min": None, "avg": None, "max": None, "mdev": None}
    return {"loss": min(r["loss"] for r in alive), "min": min(r["min"] for r in alive),
            "avg": statistics.fmean(r["avg"] for r in alive), "max": max(r["max"] for r in alive),
            "mdev": statistics.fmean(r["mdev"] for r in alive)}
