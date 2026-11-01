"""FRITZ!Box-Status ohne Anmeldung über UPnP-IGD (Port 49000, nur lesen).

Gemessen 01.11.2026 an der FRITZ!Box 6591 Cable: GetCommonLinkProperties (Kabel Up/Down, Zugangsart, Leitungs-
geschwindigkeit), GetStatusInfo (verbunden?, Laufzeit), GetExternalIPAddress (öffentliche Adresse). Funktioniert,
solange in der FRITZ!Box „Statusinformationen über UPnP übertragen“ an ist. Die Antwort wird nur mit einem
einfachen Muster gelesen (keine XML-Entitäten, kein externer Inhalt).
"""
from __future__ import annotations

import re

import httpx

_FIELD = re.compile(r"<New(\w+)>([^<]*)</New\1>")
_IFC = ("/igdupnp/control/WANCommonIFC1", "urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1")
_IP = ("/igdupnp/control/WANIPConn1", "urn:schemas-upnp-org:service:WANIPConnection:1")


def fields(xml: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _FIELD.finditer(xml or "")}


async def _soap(host: str, path: str, service: str, action: str) -> str:
    body = (f'<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            f's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            f'<u:{action} xmlns:u="{service}"/></s:Body></s:Envelope>')
    headers = {"Content-Type": 'text/xml; charset="utf-8"', "SoapAction": f"{service}#{action}"}
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await http.post(f"http://{host}:49000{path}", content=body, headers=headers)
    r.raise_for_status()
    return r.text


async def _ask(host: str, where: tuple[str, str], action: str) -> dict[str, str]:
    try:
        return fields(await _soap(host, where[0], where[1], action))
    except (OSError, httpx.HTTPError):
        return {}


def _int(v: str | None) -> int | None:
    try:
        return int(v) if v is not None else None
    except ValueError:
        return None


def _mbit(v: str | None) -> float | None:
    n = _int(v)
    return n / 1_000_000 if n is not None else None


async def status(host: str) -> dict:
    link = await _ask(host, _IFC, "GetCommonLinkProperties")
    st = await _ask(host, _IP, "GetStatusInfo")
    ip = await _ask(host, _IP, "GetExternalIPAddress")
    return {"link": link.get("PhysicalLinkStatus"), "access": link.get("WANAccessType"),
            "conn": st.get("ConnectionStatus"), "uptime_s": _int(st.get("Uptime")),
            "ext_ip": ip.get("ExternalIPAddress"), "up_max_mbit": _mbit(link.get("Layer1UpstreamMaxBitRate")),
            "down_max_mbit": _mbit(link.get("Layer1DownstreamMaxBitRate"))}
