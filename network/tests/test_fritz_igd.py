"""FRITZ!Box-Status ohne Anmeldung (UPnP-IGD, nur lesen): Kabel da? verbunden? öffentliche Adresse?"""
from __future__ import annotations

import pytest
from backend import fritz_igd

LINK = """<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>
<u:GetCommonLinkPropertiesResponse xmlns:u="urn:schemas-upnp-org:service:WANCommonInterfaceConfig:1">
<NewWANAccessType>Cable</NewWANAccessType><NewLayer1UpstreamMaxBitRate>52480000</NewLayer1UpstreamMaxBitRate>
<NewLayer1DownstreamMaxBitRate>1126400000</NewLayer1DownstreamMaxBitRate><NewPhysicalLinkStatus>Up</NewPhysicalLinkStatus>
</u:GetCommonLinkPropertiesResponse></s:Body></s:Envelope>"""
STATUS = "<s:Envelope><s:Body><u:R><NewConnectionStatus>Connected</NewConnectionStatus><NewUptime>10759</NewUptime></u:R></s:Body></s:Envelope>"
IP = "<s:Envelope><s:Body><u:R><NewExternalIPAddress>37.24.1.2</NewExternalIPAddress></u:R></s:Body></s:Envelope>"


@pytest.fixture
def soap(monkeypatch):
    calls = []
    answers = {"GetCommonLinkProperties": LINK, "GetStatusInfo": STATUS, "GetExternalIPAddress": IP}

    async def fake(host, path, service, action):
        calls.append((host, path, service, action))
        a = answers[action]
        if isinstance(a, Exception):
            raise a
        return a
    monkeypatch.setattr(fritz_igd, "_soap", fake)
    return {"calls": calls, "answers": answers}


def test_felder_lesen():
    assert fritz_igd.fields(LINK) == {"WANAccessType": "Cable", "Layer1UpstreamMaxBitRate": "52480000",
                                      "Layer1DownstreamMaxBitRate": "1126400000", "PhysicalLinkStatus": "Up"}
    assert fritz_igd.fields("kaputt") == {}


async def test_status(soap):
    s = await fritz_igd.status("192.168.3.1")
    assert s == {"link": "Up", "access": "Cable", "conn": "Connected", "uptime_s": 10759, "ext_ip": "37.24.1.2",
                 "up_max_mbit": 52.48, "down_max_mbit": 1126.4}
    assert {c[0] for c in soap["calls"]} == {"192.168.3.1"}


async def test_fritz_antwortet_nicht(soap):
    for k in soap["answers"]:
        soap["answers"][k] = OSError("weg")
    s = await fritz_igd.status("192.168.3.1")
    assert s == {"link": None, "access": None, "conn": None, "uptime_s": None, "ext_ip": None,
                 "up_max_mbit": None, "down_max_mbit": None}


async def test_teilweise(soap):
    soap["answers"]["GetExternalIPAddress"] = OSError("weg")
    s = await fritz_igd.status("192.168.3.1")
    assert s["link"] == "Up" and s["ext_ip"] is None
