"""Server-Adresse eines Mailkontos prüfen, bevor verbunden wird (Spec §11, SSRF).

Erlaubt: nur Mail-Ports und nur öffentliche Adressen. Gibt die geprüfte IP zurück – verbunden wird genau mit dieser
(kein DNS-Rebinding zwischen Prüfung und Verbindung; der Hostname dient nur noch für TLS/SNI).
Ein eigener Mailserver im Heimnetz geht nur über eine ausdrückliche Admin-Freigabe des Hostnamens.
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from collections.abc import Callable, Iterable

from hydrahive.net.ssrf import BLOCKED_HOSTNAMES, _ip_is_internal

MAIL_PORTS = frozenset({993, 143, 465, 587, 25})


class HostBlocked(ValueError):
    pass


def _system_resolve(host: str) -> list[str]:
    return [i[4][0] for i in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)]


def check(host: str, port: int, *, resolve: Callable[[str], list[str]] = _system_resolve,
          allow_internal: Iterable[str] = ()) -> str:
    if not isinstance(port, int) or port not in MAIL_PORTS:
        raise HostBlocked("nur Mail-Ports erlaubt (993, 143, 465, 587, 25)")
    if not isinstance(host, str) or not host.strip() or len(host) > 253:
        raise HostBlocked("Server fehlt")
    name = host.strip().lower().rstrip(".")
    trusted = name in {h.strip().lower().rstrip(".") for h in allow_internal}
    if name in BLOCKED_HOSTNAMES and not trusted:
        raise HostBlocked("interne Adresse")
    try:
        ips = [ipaddress.ip_address(name)]
    except ValueError:
        try:
            ips = [ipaddress.ip_address(a) for a in resolve(name)]
        except (OSError, ValueError) as e:
            raise HostBlocked("Server nicht auflösbar") from e
    if not ips:
        raise HostBlocked("Server nicht auflösbar")
    if not trusted and any(_ip_is_internal(ip) for ip in ips):
        raise HostBlocked("interne Adresse – nur mit Freigabe durch den Admin")
    first = ips[0]
    if isinstance(first, ipaddress.IPv6Address) and first.ipv4_mapped is not None:
        first = first.ipv4_mapped
    return str(first)


_HOSTNAME = re.compile(r"^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$")


def allowed_from_env() -> set[str]:
    """Admin-Freigabe für Mailserver im Heimnetz (Spec §11): HH_MAILBOX_ALLOW_INTERNAL in /etc/hydrahive2/env,
    Hostnamen/IPs durch Komma getrennt. Nur genau diese Namen – keine Muster, keine Netzbereiche."""
    out = set()
    for part in os.environ.get("HH_MAILBOX_ALLOW_INTERNAL", "").split(","):
        name = part.strip().lower().rstrip(".")
        if _HOSTNAME.match(name):
            out.add(name)
    return out
