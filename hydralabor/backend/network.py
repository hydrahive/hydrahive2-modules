"""Eigenes Netz + ACL für das Hydra-Labor (PLAN-L1.md).

incus nur über backend.incus.run (feste Argumentlisten, keine Shell auf dem Server). Reihenfolge: ACL → Netz →
ACL ans Netz. Die Probe läuft IM Labor-Container und prüft, dass Server/LAN/Tailscale zu sind und DNS geht.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from . import incus

NET = "hhlabor0"
ACL = "hhlabor-acl"
_CANDIDATES = ("10.77.0.0/24", "10.78.0.0/24", "172.31.77.0/24")
_PRIVATE = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16",
            "127.0.0.0/8", "fc00::/7", "fe80::/10")


class LaborNetworkError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class NetworkState:
    name: str
    acl: str
    subnet: str


def _ip_json(*args: str) -> list:
    try:
        p = subprocess.run(["ip", "-j", *args], capture_output=True, text=True, timeout=10, check=False)
        return json.loads(p.stdout or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def _host_networks() -> set[str]:
    return {str(r["dst"]) for r in _ip_json("route") if r.get("dst") not in (None, "default")}


def _host_addresses() -> set[str]:
    return {a["local"] + "/32" for i in _ip_json("addr") for a in i.get("addr_info", [])
            if a.get("family") == "inet" and a.get("local")}


def choose_subnet() -> str:
    routes = _host_networks()
    for c in _CANDIDATES:
        if c not in routes:
            return c
    raise LaborNetworkError("labor_subnet_unavailable")


async def _call(*args: str) -> None:
    rc, _, _ = await incus.run(*args)
    if rc != 0:
        raise LaborNetworkError("labor_incus_failed")


async def _names(*kind: str) -> set[str]:
    rc, out, _ = await incus.run(*kind, "list", "--format", "csv", "-c", "n")
    return set(out.split()) if rc == 0 else set()


async def ensure_network() -> NetworkState:
    """Legt ACL und Netz an, wenn sie fehlen. Bestehende werden nicht doppelt angelegt."""
    have_acl = ACL in await _names("network", "acl")
    have_net = NET in await _names("network")
    if have_acl and have_net:
        return NetworkState(NET, ACL, "")
    subnet = choose_subnet()
    if not have_acl:
        await _call("network", "acl", "create", ACL)
        dest = ",".join(_PRIVATE + tuple(sorted(_host_addresses())))
        await _call("network", "acl", "rule", "add", ACL, "egress", "action=reject", f"destination={dest}",
                    "state=enabled")
        await _call("network", "acl", "rule", "add", ACL, "egress", "action=allow", "state=enabled")
    if not have_net:
        gw = subnet.replace(".0/24", ".1/24")
        await _call("network", "create", NET, f"ipv4.address={gw}", "ipv4.nat=true", "ipv6.address=none")
    await _call("network", "set", NET, f"security.acls={ACL}")
    return NetworkState(NET, ACL, subnet)


def probe_targets(gateway: str) -> list[str]:
    """Ziele, die aus dem Labor ZU sein müssen: Gateway des Labor-Netzes + alle eigenen Adressen des Servers."""
    hosts = {gateway, *(a.split("/")[0] for a in _host_addresses())}
    return [f"{h}:{p}" for h in sorted(hosts) for p in (22, 443)]


async def probe(container: str, gateway: str) -> dict:
    targets = probe_targets(gateway)
    script = ("PROBE_TARGETS=" + ",".join(targets) + " ; # hh-labor-netprobe\n"
              'for t in $(echo "$PROBE_TARGETS" | tr , " "); do '
              'timeout 3 bash -c "echo > /dev/tcp/${t%:*}/${t#*:}" 2>/dev/null && echo "$t offen" || echo "$t zu"; done; '
              'getent hosts github.com >/dev/null && echo "dns ok" || echo "dns fehler"')
    rc, out, _ = await incus.run("exec", container, "--", "bash", "-c", script, timeout=60)
    if rc != 0:
        raise LaborNetworkError("labor_net_probe_failed")
    lines = [ln.strip() for ln in out.splitlines()]
    if any(ln.endswith(" offen") for ln in lines):
        raise LaborNetworkError("labor_net_open")
    if "dns ok" not in lines:
        raise LaborNetworkError("labor_dns_failed")
    return {"ok": True, "checked": len(targets)}


async def gateway() -> str:
    raise NotImplementedError


async def remove() -> None:
    raise NotImplementedError
