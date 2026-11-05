"""Weg Server → Container für die Vorschau (PLAN-V1.md Entscheidung 8; Muster hydralabor probe_net.py).

Eingang nur vom Gateway des Vibe-Netzes (= der Server), nur TCP 5173. Ausgehend bleibt alles wie zuvor zu: ein Vibe-
Container erreicht weiterhin weder Server noch Heimnetz. Dazu die Adresse eines Containers für nginx.
"""
from __future__ import annotations

import ipaddress
import re
import time

from . import container, incus, network

PORT = 5173
_CACHE_SECONDS = 20.0
_addr: dict[str, tuple[str, float]] = {}
_IPV4 = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})")


async def _rule() -> list[str]:
    return ["action=allow", f"source={await network.gateway()}/32", "protocol=tcp", f"destination_port={PORT}"]


async def _ingress() -> list[dict]:
    import yaml
    rc, out, _ = await incus.run("network", "acl", "show", network.ACL)
    if rc != 0:
        raise network.VibeNetworkError("vibe_network_missing")
    return (yaml.safe_load(out) or {}).get("ingress") or []


def _match(r: dict, want: list[str]) -> bool:
    return all(str(r.get(k)) == v for k, _, v in (w.partition("=") for w in want))


async def is_open() -> bool:
    want = await _rule()
    return any(_match(r, want) for r in await _ingress())


async def open_port() -> None:
    """Idempotent: die Regel gibt es nach dem Aufruf genau einmal."""
    if await is_open():
        return
    rc, _, _ = await incus.run("network", "acl", "rule", "add", network.ACL, "ingress", *await _rule(), "state=enabled")
    if rc != 0:
        raise network.VibeNetworkError("vibe_incus_failed")


async def address(project_id: str) -> str | None:
    """`ip:5173` des Containers (nur eine private IPv4), kurz gemerkt. None = keine Adresse (Container aus)."""
    now = time.monotonic()
    hit = _addr.get(project_id)
    if hit and hit[1] > now:
        return hit[0]
    rc, out, _ = await incus.run("list", container.name_for(project_id), "--format", "csv", "-c", "4", timeout=15)
    m = _IPV4.search(out) if rc == 0 else None
    try:
        ip = ipaddress.IPv4Address(m.group(1)) if m else None
    except ValueError:
        ip = None
    if ip is None or not ip.is_private:
        _addr.pop(project_id, None)
        return None
    _addr[project_id] = (f"{ip}:{PORT}", now + _CACHE_SECONDS)
    return _addr[project_id][0]
