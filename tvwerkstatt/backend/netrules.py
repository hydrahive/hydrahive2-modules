"""Regeln der Sperrliste hhtvw-acl, rein berechnet (PLAN-E1.md Baustein 2).

Grundsatz: Internet ja, alles Private nein. Ausnahme je eingetragenem Fernseher: nur TCP auf seinen ADB-Port.
incus wertet `reject` vor `allow` (Befund hydralabor, 30.10.), deshalb wird die Adresse des Fernsehers aus den
gesperrten Bereichen herausgerechnet und für ihn eigene Sperren gesetzt: TCP auf allen anderen Ports, UDP und ICMP ganz.
"""
from __future__ import annotations

import ipaddress

PRIVATE = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16", "127.0.0.0/8",
           "fc00::/7", "fe80::/10")


class TvwNetworkError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def check_tv(address: str, port: int, host_addresses: set[str]) -> ipaddress.IPv4Address:
    """Nur eine einzelne IPv4-Adresse im privaten Heimnetz, nicht der Server selbst, Port 1–65535."""
    try:
        ip = ipaddress.IPv4Address(address)
    except (ipaddress.AddressValueError, ValueError):
        raise TvwNetworkError("tvw_bad_address") from None
    own = {a.split("/")[0] for a in host_addresses}
    if not ip.is_private or ip.is_loopback or ip.is_link_local or str(ip) in own:
        raise TvwNetworkError("tvw_bad_address")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise TvwNetworkError("tvw_bad_address")
    return ip


def _without(blocks: list[str], holes: list[ipaddress.IPv4Address]) -> list[str]:
    """Die Bereiche, aus denen die Einzeladressen herausgeschnitten sind."""
    nets = [ipaddress.ip_network(b) for b in blocks]
    for hole in holes:
        cut = ipaddress.ip_network(f"{hole}/32")
        nxt = []
        for n in nets:
            if n.version == 4 and cut.subnet_of(n):
                nxt.extend(n.address_exclude(cut) if n != cut else [])
            else:
                nxt.append(n)
        nets = nxt
    v4 = sorted((n for n in nets if n.version == 4), key=lambda n: (int(n.network_address), n.prefixlen))
    v6 = [n for n in nets if n.version == 6]
    return [str(n) for n in v4 + v6]


def _ports_except(port: int) -> str:
    parts = []
    if port > 1:
        parts.append(f"1-{port - 1}" if port > 2 else "1")
    if port < 65535:
        parts.append(f"{port + 1}-65535" if port < 65534 else "65535")
    return ",".join(parts)


def rules(tvs: list[tuple[str, int]], host_addresses: set[str]) -> list[dict[str, str]]:
    """Alle Ausgangsregeln in fester Reihenfolge. Gleiche Eingabe, gleiche Regeln (zum Vergleich mit dem Ist)."""
    ips = [(check_tv(a, p, host_addresses), p) for a, p in sorted(set(tvs))]
    blocks = list(PRIVATE) + sorted(host_addresses)
    out = [{"action": "reject", "destination": ",".join(_without(blocks, [ip for ip, _ in ips])), "state": "enabled"}]
    for ip, port in ips:
        dest = f"{ip}/32"
        out.append({"action": "reject", "destination": dest, "destination_port": _ports_except(port),
                    "protocol": "tcp", "state": "enabled"})
        out.append({"action": "reject", "destination": dest, "protocol": "udp", "state": "enabled"})
        out.append({"action": "reject", "destination": dest, "protocol": "icmp4", "state": "enabled"})
    out.append({"action": "allow", "state": "enabled"})
    return out


def same(a: list[dict], b: list[dict]) -> bool:
    """Gleiche Regeln, Reihenfolge egal: incus wertet reject vor allow unabhängig von der Reihenfolge."""
    key = lambda r: tuple(sorted(r.items()))  # noqa: E731
    return sorted(map(key, a)) == sorted(map(key, b))


def has_duplicates(rs: list[dict]) -> bool:
    keys = [tuple(sorted(r.items())) for r in rs]
    return len(keys) != len(set(keys))


def rule_args(rule: dict[str, str]) -> list[str]:
    """Regel als `key=value`-Liste für `incus network acl rule add/remove` (feste Reihenfolge)."""
    order = ("action", "destination", "destination_port", "protocol", "state")
    return [f"{k}={rule[k]}" for k in order if k in rule]
