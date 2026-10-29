"""Was wirklich an den Fernseher geht (echtes _post mit nachgebautem Netz, httpx.MockTransport)."""
from __future__ import annotations

import json

import httpx
import pytest
from backend import client

PSK = "draht-psk-99"


@pytest.fixture
def wire(monkeypatch):
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"result": [{"status": "active"}], "id": 1})

    real = httpx.AsyncClient

    def fake_client(*a, **kw):
        kw["transport"] = httpx.MockTransport(handler)
        return real(*a, **kw)

    monkeypatch.setattr(client.httpx, "AsyncClient", fake_client)
    return seen


async def test_anfrage_an_sony_pfad_mit_schluessel_nur_in_kopfzeile(wire):
    status, data = await client._post("192.168.178.186", "system", "getPowerStatus", [], "1.0", PSK)
    assert status == 200 and data["result"][0]["status"] == "active"
    req = wire[-1]
    assert str(req.url) == "http://192.168.178.186/sony/system" and req.method == "POST"
    assert req.headers["X-Auth-PSK"] == PSK
    body = json.loads(req.content)
    assert body == {"method": "getPowerStatus", "id": 1, "params": [], "version": "1.0"}
    assert PSK not in req.content.decode()


async def test_ohne_schluessel_keine_kopfzeile(wire):
    await client._post("192.168.178.186", "system", "getInterfaceInformation", [], "1.0", "")
    assert "X-Auth-PSK" not in wire[-1].headers


async def test_keine_weiterleitung_folgen(monkeypatch):
    """Ein Fernseher (oder etwas, das sich so ausgibt) darf die Anfrage nicht woandershin umleiten."""
    hits: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        hits.append(str(req.url))
        return httpx.Response(302, headers={"Location": "http://8.8.8.8/x"})

    real = httpx.AsyncClient
    monkeypatch.setattr(client.httpx, "AsyncClient",
                        lambda *a, **kw: real(*a, **{**kw, "transport": httpx.MockTransport(handler)}))
    status, _ = await client._post("192.168.178.186", "system", "getPowerStatus", [], "1.0", PSK)
    assert status == 302 and hits == ["http://192.168.178.186/sony/system"]
