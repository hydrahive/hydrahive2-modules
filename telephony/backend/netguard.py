"""Anlagenadresse nur im Heimnetz (SPEC-V1 §2.14, §16.4).

Erlaubt sind nur private IPv4-Adressen (RFC 1918), direkt oder als Name (z. B. ``fritz.box``). Alle aufgelösten Adressen
müssen privat sein. Zurück kommt die geprüfte IP: Verbunden wird genau mit ihr, damit sich die Adresse zwischen Prüfung
und Verbindung nicht ändern kann.
"""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable

_PRIVATE = tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


class Blocked(ValueError):
    """Adresse nicht erlaubt oder nicht auflösbar."""


def _system_resolve(host: str) -> list[str]:
    return [i[4][0] for i in socket.getaddrinfo(host, None, family=socket.AF_INET, proto=socket.IPPROTO_UDP)]


def _private(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return isinstance(ip, ipaddress.IPv4Address) and any(ip in n for n in _PRIVATE)


def check(host: str, *, resolve: Callable[[str], list[str]] = _system_resolve) -> str:
    name = (host or "").strip().lower().rstrip(".")
    if not name:
        raise Blocked("Adresse fehlt")
    try:
        ips = [ipaddress.ip_address(name)]
    except ValueError:
        try:
            ips = [ipaddress.ip_address(a) for a in resolve(name)]
        except (OSError, ValueError) as e:
            raise Blocked("Adresse nicht auflösbar") from e
    if not ips:
        raise Blocked("Adresse nicht auflösbar")
    if not all(_private(ip) for ip in ips):
        raise Blocked("nur Adressen im Heimnetz erlaubt")
    return str(ips[0])
