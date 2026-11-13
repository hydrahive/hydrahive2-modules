"""Eigenes Netz hhtvw0 + Sperrliste hhtvw-acl für den Container der TV-Werkstatt (PLAN-E1.md Baustein 2).

Muster vibe/backend/network.py. Eigene Namen und Teilnetze, damit Vibe, Labor und TV-Werkstatt nebeneinander laufen.
incus nur über backend.incus.run (feste Argumentlisten, keine Shell auf dem Server). Reihenfolge: Sperrliste → Netz →
Sperrliste ans Netz. Die Regeln selbst berechnet netrules.py; hier wird nur angelegt, verglichen und nachgezogen.
"""
from __future__ import annotations

import json
import subprocess

from . import incus, netrules
from .netrules import TvwNetworkError

__all__ = ["ACL", "NET", "TvwNetworkError", "choose_subnet", "ensure_network", "gateway", "probe", "probe_targets",
           "remove_if_unused", "rules", "sync_rules"]

NET = "hhtvw0"
ACL = "hhtvw-acl"
_CANDIDATES = ("10.81.0.0/24", "10.82.0.0/24", "172.31.81.0/24")
_NEVER = ("192.168.178.1", "192.168.178.3")        # Router und Fritzbox von Till: nie ansprechen, auch nicht zur Probe


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
    raise TvwNetworkError("tvw_subnet_unavailable")


def rules(tvs: list[tuple[str, int]]) -> list[dict[str, str]]:
    return netrules.rules(tvs, _host_addresses())


async def _call(*args: str) -> None:
    rc, _, _ = await incus.run(*args)
    if rc != 0:
        raise TvwNetworkError("tvw_incus_failed")


async def _names(*kind: str) -> set[str]:
    rc, out, _ = await incus.run(*kind, "list", "--format", "csv")
    return incus.first_column(out) if rc == 0 else set()


async def sync_rules(tvs: list[tuple[str, int]]) -> bool:
    """Regeln an Fernseher und Serveradressen anpassen. Erst die neuen dazu, dann die alten weg – nie ein Moment ohne
    Sperre. True, wenn etwas geändert wurde."""
    import yaml
    want = rules(tvs)
    rc, out, _ = await incus.run("network", "acl", "show", ACL)
    if rc != 0:
        raise TvwNetworkError("tvw_network_missing")
    have = (yaml.safe_load(out) or {}).get("egress") or []
    if netrules.has_duplicates(have):
        raise TvwNetworkError("tvw_acl_dirty")    # einzeln nicht entfernbar, --force hieße kurz ohne Sperre
    if netrules.same(have, want):
        return False
    for r in [r for r in want if r not in have and r["action"] == "reject"]:
        await _call("network", "acl", "rule", "add", ACL, "egress", *netrules.rule_args(r))
    for r in [r for r in have if r not in want]:
        await _call("network", "acl", "rule", "remove", ACL, "egress", *netrules.rule_args(r))
    if {"action": "allow", "state": "enabled"} not in have:
        await _call("network", "acl", "rule", "add", ACL, "egress", "action=allow", "state=enabled")
    return True


async def ensure_network(tvs: list[tuple[str, int]]) -> None:
    """Legt Sperrliste und Netz an, wenn sie fehlen, und zieht die Regeln nach. Ohne raw.dnsmasq-Sperre: der Container
    bekommt Namensdienst und Adresse vom Netz (Fund Probelauf 13.11. auf hhnat0)."""
    if ACL not in await _names("network", "acl"):
        await _call("network", "acl", "create", ACL)
        for r in rules(tvs):
            await _call("network", "acl", "rule", "add", ACL, "egress", *netrules.rule_args(r))
    else:
        await sync_rules(tvs)
    if NET not in await _names("network"):
        subnet = choose_subnet()
        await _call("network", "create", NET, f"ipv4.address={subnet.replace('.0/24', '.1')}/24", "ipv4.nat=true",
                    "ipv6.address=none")
    await _call("network", "set", NET, f"security.acls={ACL}")


async def gateway() -> str:
    rc, out, _ = await incus.run("network", "get", NET, "ipv4.address")
    gw = out.strip().split("/")[0]
    if rc != 0 or not gw:
        raise TvwNetworkError("tvw_network_missing")
    return gw


def probe_targets(gw: str, tvs: list[tuple[str, int]]) -> dict[str, list[str]]:
    """`closed` muss zu sein (Gateway, Server, andere Ports des Fernsehers), `tv` darf offen sein."""
    hosts = sorted({gw, *(a.split("/")[0] for a in _host_addresses())} - set(_NEVER))
    closed = [f"{h}:{p}" for h in hosts for p in (22, 443)]
    closed += [f"{a}:80" for a, _ in sorted(set(tvs)) if a not in _NEVER]
    return {"closed": closed, "tv": [f"{a}:{p}" for a, p in sorted(set(tvs)) if a not in _NEVER]}


async def probe(container: str, gw: str, tvs: list[tuple[str, int]]) -> dict:
    t = probe_targets(gw, tvs)
    script = ("PROBE_TARGETS=" + ",".join(t["closed"] + t["tv"]) + " ; # hh-tvw-netprobe\n"
              'for t in $(echo "$PROBE_TARGETS" | tr , " "); do '
              'timeout 3 bash -c "echo > /dev/tcp/${t%:*}/${t#*:}" 2>/dev/null && echo "$t offen" || echo "$t zu"; done; '
              'getent hosts dl.google.com >/dev/null && echo "dns ok" || echo "dns fehler"')
    rc, out, _ = await incus.run("exec", container, "--", "bash", "-c", script, timeout=90)
    if rc != 0:
        raise TvwNetworkError("tvw_net_probe_failed")
    seen = dict(ln.rsplit(" ", 1) for ln in out.splitlines() if ln.count(":") == 1 and " " in ln)
    if set(seen) != set(t["closed"] + t["tv"]):
        raise TvwNetworkError("tvw_net_probe_failed")
    if any(seen[x] == "offen" for x in t["closed"]):
        raise TvwNetworkError("tvw_net_open")
    if "dns ok" not in out.splitlines():
        raise TvwNetworkError("tvw_dns_failed")
    return {"ok": True, "checked": len(t["closed"]), "tv": {x: seen[x] for x in t["tv"]}}


async def remove_if_unused() -> bool:
    """Netz und Sperrliste weg, wenn KEIN Container daran hängt. Unlesbare Liste → gilt als benutzt."""
    rc, out, _ = await incus.run("list", "--format", "json")
    if rc != 0:
        return False
    try:
        items = json.loads(out or "[]")
    except ValueError:
        return False
    if any(d.get("network") == NET for i in items for d in (i.get("expanded_devices") or {}).values()):
        return False
    await incus.run("network", "delete", NET)
    await incus.run("network", "acl", "delete", ACL)
    return True
