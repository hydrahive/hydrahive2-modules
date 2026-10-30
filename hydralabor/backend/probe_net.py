"""L3 (PLAN-L3.md Baustein 4): eingehende Regel für die Probe – nur vom Gateway des Labor-Netzes (= Server), nur
TCP 8001. Ausgehend bleibt alles wie in L1: das Labor erreicht den Server weiterhin nicht (gemessen 30.10.).
"""
from __future__ import annotations

import yaml

from . import incus, network

PORT = 8001


async def _rule() -> list[str]:
    gw = await network.gateway()
    return ["action=allow", f"source={gw}/32", "protocol=tcp", f"destination_port={PORT}"]


async def _ingress() -> list[dict]:
    rc, out, _ = await incus.run("network", "acl", "show", network.ACL)
    if rc != 0:
        raise network.LaborNetworkError("labor_network_missing")
    return (yaml.safe_load(out) or {}).get("ingress") or []


def _match(r: dict, want: list[str]) -> bool:
    return all(str(r.get(k)) == v for k, _, v in (w.partition("=") for w in want))


async def is_open() -> bool:
    want = await _rule()
    return any(_match(r, want) for r in await _ingress())


async def open_port() -> None:
    if await is_open():
        return
    rc, _, _ = await incus.run("network", "acl", "rule", "add", network.ACL, "ingress", *await _rule(), "state=enabled")
    if rc != 0:
        raise network.LaborNetworkError("labor_incus_failed")


async def close_port() -> None:
    if not await is_open():
        return
    rc, _, _ = await incus.run("network", "acl", "rule", "remove", network.ACL, "ingress", *await _rule())
    if rc != 0:
        raise network.LaborNetworkError("labor_incus_failed")
