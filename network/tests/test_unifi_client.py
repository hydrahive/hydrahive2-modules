"""Zugriff auf die Dream Machine: Schlüssel nur als X-API-KEY, nur mit bestätigtem Zertifikat, Fehler als Code."""
from __future__ import annotations

import pytest
from backend import pinned, unifi_client
from backend.errors import NetError

PIN = "ab" * 32


class Resp:
    def __init__(self, status, data=None, text=""):
        self.status_code = status
        self._data = data
        self.text = text

    def json(self):
        if self._data is None:
            raise ValueError("kein json")
        return self._data


@pytest.fixture
def send(monkeypatch):
    calls = []
    state = {"resp": Resp(200, {"applicationVersion": "10.6.109"}), "exc": None}

    async def fake(method, url, *, headers, json, pin):
        calls.append({"method": method, "url": url, "headers": headers, "json": json, "pin": pin})
        if state["exc"]:
            raise state["exc"]
        return state["resp"]
    monkeypatch.setattr(unifi_client, "_send", fake)
    return {"calls": calls, "state": state}


async def test_schluessel_im_richtigen_kopf(send):
    c = unifi_client.Udm("https://192.168.178.1", "SCHLUESSEL", PIN)
    assert await c.get("/proxy/network/integration/v1/info") == {"applicationVersion": "10.6.109"}
    call = send["calls"][0]
    assert call["url"] == "https://192.168.178.1/proxy/network/integration/v1/info"
    assert call["headers"]["X-API-KEY"] == "SCHLUESSEL"
    assert "Authorization" not in call["headers"]
    assert call["pin"] == PIN and call["method"] == "GET"


async def test_post_mit_inhalt(send):
    c = unifi_client.Udm("https://192.168.178.1:8443/", "K", PIN)
    await c.post("/x", {"a": 1})
    assert send["calls"][0]["url"] == "https://192.168.178.1:8443/x"
    assert send["calls"][0]["json"] == {"a": 1} and send["calls"][0]["method"] == "POST"


async def test_ohne_bestaetigtes_zertifikat_keine_anfrage(send):
    c = unifi_client.Udm("https://192.168.178.1", "K", None)
    with pytest.raises(NetError) as e:
        await c.get("/x")
    assert e.value.code == "network_cert_unconfirmed" and send["calls"] == []


@pytest.mark.parametrize("status,code", [(401, "network_auth_failed"), (403, "network_auth_failed"),
                                         (404, "network_bad_response"), (500, "network_bad_response")])
async def test_fehler_status(send, status, code):
    send["state"]["resp"] = Resp(status, {"error": "x"})
    with pytest.raises(NetError) as e:
        await unifi_client.Udm("https://192.168.178.1", "K", PIN).get("/x")
    assert e.value.code == code


async def test_kein_json(send):
    send["state"]["resp"] = Resp(200, None, "<html>")
    with pytest.raises(NetError) as e:
        await unifi_client.Udm("https://192.168.178.1", "K", PIN).get("/x")
    assert e.value.code == "network_bad_response"


async def test_zertifikat_geaendert(send):
    send["state"]["exc"] = pinned.PinMismatch("cd" * 32)
    with pytest.raises(NetError) as e:
        await unifi_client.Udm("https://192.168.178.1", "K", PIN).get("/x")
    assert e.value.code == "network_cert_changed"


async def test_nicht_erreichbar(send):
    send["state"]["exc"] = OSError("timeout")
    with pytest.raises(NetError) as e:
        await unifi_client.Udm("https://192.168.178.1", "K", PIN).get("/x")
    assert e.value.code == "network_unreachable"
    assert "K" not in str(e.value)


def test_fingerabdruck_format():
    assert pinned.fingerprint(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert pinned.pretty("ba7816bf" + "0" * 56).startswith("BA:78:16:BF")


async def test_trace_lehnt_fremdes_zertifikat_ab():
    class Ssl:
        def getpeercert(self, binary_form=False):
            return b"anderes"

    class Stream:
        def get_extra_info(self, k):
            return Ssl() if k == "ssl_object" else None
    trace = pinned.make_trace(pinned.fingerprint(b"richtig"))
    with pytest.raises(pinned.PinMismatch):
        await trace("connection.start_tls.complete", {"return_value": Stream()})
    ok = pinned.make_trace(pinned.fingerprint(b"anderes"))
    await ok("connection.start_tls.complete", {"return_value": Stream()})
    await ok("http11.send_request_headers.started", {})


async def test_trace_ohne_zertifikat_lehnt_ab():
    class Stream:
        def get_extra_info(self, k):
            return None
    with pytest.raises(pinned.PinMismatch):
        await pinned.make_trace("ab" * 32)("connection.start_tls.complete", {"return_value": Stream()})


async def test_geheimnisse_werden_beim_empfang_verworfen(send):
    send["state"]["resp"] = Resp(200, {"data": [{"name": "Heimnetz", "x_passphrase": "LOCKVOGEL", "inner": {"x_k": "LOCKVOGEL"}}]})
    got = await unifi_client.Udm("https://192.168.178.1", "K", PIN).get("/proxy/network/api/s/default/rest/wlanconf")
    assert got == {"data": [{"name": "Heimnetz", "inner": {}}]}
    assert "LOCKVOGEL" not in str(got)
