"""Weg ins Internet erkennen: Kabel, Mobilfunk-Ersatz an der FRITZ!Box (USB) oder gar keiner.

Belege (01.11.2026): Bei Kabel meldet die FRITZ!Box PhysicalLinkStatus „Up“ und eine öffentliche Vodafone-Adresse.
Beim Mobilfunk-Ersatz ist das Kabel „Down“ bzw. die Adresse ist eine Mobilfunk-Adresse hinter Carrier-NAT
(100.64.0.0/10 oder privat). Für alte Stundenwerte ohne FRITZ!Box-Daten gibt es nur eine Vermutung aus der
kürzesten Antwortzeit (Kabel 7–9 ms, Mobilfunk ≥ 18 ms).
"""
from __future__ import annotations

import ipaddress

_CGNAT = ipaddress.ip_network("100.64.0.0/10")
MOBILE_MIN_MS = 18


def _mobile_ip(ip: str | None) -> bool:
    try:
        a = ipaddress.ip_address(ip or "")
    except ValueError:
        return False
    return a in _CGNAT or a.is_private


def path(inet_loss: float | None, link: str | None, ext_ip: str | None) -> str:
    if inet_loss is None:
        return "unknown"
    if inet_loss >= 100.0:
        return "none"
    if link is None:
        return "unknown"
    if link != "Up" or _mobile_ip(ext_ip):
        return "mobile"
    return "cable"


def guess_hour(lat_min: float | None, lat_avg: float | None) -> str:
    if lat_min is None or lat_avg is None:
        return "unknown"
    if lat_avg == 0:
        return "none"
    if lat_min == 0:
        return "unknown"
    return "mobile" if lat_min >= MOBILE_MIN_MS else "cable"
