"""Eigenes Netz + ACL für Vibe (PLAN-V1.md Entscheidung 2; Kopie aus hydralabor/backend/network.py).

Ein Netz für ALLE Vibe-Projekte. Eigener Name und eigene Teilnetze, damit Vibe und Hydra-Labor nebeneinander laufen und
keines das Netz des anderen anfasst. incus nur über backend.incus.run (feste Argumentlisten, keine Shell auf dem
Server). Reihenfolge: ACL → Netz → ACL ans Netz. Die Probe läuft IM Container und prüft, dass Server/LAN/Tailscale zu
sind und DNS geht. Die Probe-Ziele sind das Gateway und die eigenen Adressen des Servers – nie der Router.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from . import incus

NET = "hhvibe0"
ACL = "hhvibe-acl"
PREFIX = "hh-vibe-"
_CANDIDATES = ("10.79.0.0/24", "10.80.0.0/24", "172.31.79.0/24")
_PRIVATE = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16",
            "127.0.0.0/8", "fc00::/7", "fe80::/10")


class VibeNetworkError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class NetworkState:
    name: str
    acl: str
    subnet: str           # leer = gab es schon (nicht von diesem Aufruf angelegt)


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
    raise VibeNetworkError("vibe_subnet_unavailable")


def gateway_of(subnet: str) -> str:
    """Gateway-Adresse (ohne /24) eines Teilnetzes `a.b.c.0/24`."""
    return subnet.replace(".0/24", ".1")


async def _call(*args: str) -> None:
    rc, _, _ = await incus.run(*args)
    if rc != 0:
        raise VibeNetworkError("vibe_incus_failed")


async def _names(*kind: str) -> set[str]:
    rc, out, _ = await incus.run(*kind, "list", "--format", "csv")
    return incus.first_column(out) if rc == 0 else set()


def _dest() -> str:
    return ",".join(_PRIVATE + tuple(sorted(_host_addresses())))


async def sync_rules() -> bool:
    """Sperrliste an die aktuellen Adressen des Servers anpassen. Erst die neue Regel, dann die alte weg – nie ein
    Moment ohne Sperre (Befund Labor hydratest 30.10.: incus wertet reject trotz Reihenfolge vor allow).
    Gibt True zurück, wenn etwas geändert wurde."""
    import yaml
    rc, out, _ = await incus.run("network", "acl", "show", ACL)
    if rc != 0:
        raise VibeNetworkError("vibe_network_missing")
    rules = (yaml.safe_load(out) or {}).get("egress") or []
    old = [r.get("destination", "") for r in rules if r.get("action") == "reject"]
    want = _dest()
    if old == [want]:
        return False
    await _call("network", "acl", "rule", "add", ACL, "egress", "action=reject", f"destination={want}",
                "state=enabled")
    for d in old:
        await _call("network", "acl", "rule", "remove", ACL, "egress", "action=reject", f"destination={d}")
    return True


async def ensure_network() -> NetworkState:
    """Legt ACL und Netz an, wenn sie fehlen. Bestehende werden nicht doppelt angelegt."""
    have_acl = ACL in await _names("network", "acl")
    have_net = NET in await _names("network")
    if have_acl and have_net:
        return NetworkState(NET, ACL, "")
    subnet = choose_subnet()
    if not have_acl:
        await _call("network", "acl", "create", ACL)
        await _call("network", "acl", "rule", "add", ACL, "egress", "action=reject", f"destination={_dest()}",
                    "state=enabled")
        await _call("network", "acl", "rule", "add", ACL, "egress", "action=allow", "state=enabled")
    if not have_net:
        await _call("network", "create", NET, f"ipv4.address={gateway_of(subnet)}/24", "ipv4.nat=true",
                    "ipv6.address=none")
    await _call("network", "set", NET, f"security.acls={ACL}")
    return NetworkState(NET, ACL, subnet)


def probe_targets(gateway: str) -> list[str]:
    """Ziele, die aus dem Container ZU sein müssen: Gateway des Vibe-Netzes + alle eigenen Adressen des Servers."""
    hosts = {gateway, *(a.split("/")[0] for a in _host_addresses())}
    return [f"{h}:{p}" for h in sorted(hosts) for p in (22, 443)]


async def probe(container: str, gateway: str) -> dict:
    targets = probe_targets(gateway)
    script = ("PROBE_TARGETS=" + ",".join(targets) + " ; # hh-vibe-netprobe\n"
              'for t in $(echo "$PROBE_TARGETS" | tr , " "); do '
              'timeout 3 bash -c "echo > /dev/tcp/${t%:*}/${t#*:}" 2>/dev/null && echo "$t offen" || echo "$t zu"; done; '
              'getent hosts github.com >/dev/null && echo "dns ok" || echo "dns fehler"')
    rc, out, _ = await incus.run("exec", container, "--", "bash", "-c", script, timeout=60)
    if rc != 0:
        raise VibeNetworkError("vibe_net_probe_failed")
    lines = [ln.strip() for ln in out.splitlines()]
    if any(ln.endswith(" offen") for ln in lines):
        raise VibeNetworkError("vibe_net_open")
    if "dns ok" not in lines:
        raise VibeNetworkError("vibe_dns_failed")
    return {"ok": True, "checked": len(targets)}


async def gateway() -> str:
    """Gateway-IP des Vibe-Netzes (ohne /24)."""
    rc, out, _ = await incus.run("network", "get", NET, "ipv4.address")
    gw = out.strip().split("/")[0]
    if rc != 0 or not gw:
        raise VibeNetworkError("vibe_network_missing")
    return gw


async def _vibe_containers_on_net() -> set[str] | None:
    """Namen aller Container (nicht nur Vibe-eigene), die am Vibe-Netz hängen. None = Liste nicht lesbar."""
    rc, out, _ = await incus.run("list", "--format", "json")
    if rc != 0:
        return None
    try:
        items = json.loads(out or "[]")
    except ValueError:
        return None
    return {i.get("name", "") for i in items
            if any(d.get("network") == NET for d in (i.get("expanded_devices") or {}).values())}


async def remove_if_unused() -> bool:
    """Netz und Sperrliste weg, wenn KEIN Container mehr daran hängt. Nur die eigenen Namen (fest im Modul).
    Nicht lesbare Containerliste → das Netz gilt als benutzt (fail-closed). True = abgeräumt."""
    users = await _vibe_containers_on_net()
    if users is None or users:
        return False
    await incus.run("network", "delete", NET)
    await incus.run("network", "acl", "delete", ACL)
    return True
