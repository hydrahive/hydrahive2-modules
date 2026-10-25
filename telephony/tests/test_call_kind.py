"""Anrufart in der Anrufliste: Ansage oder Assistent (Till 25.10.: sonst sieht man nicht, was gelaufen ist)."""
from __future__ import annotations

from typing import ClassVar

import pytest

pytestmark = pytest.mark.usefixtures("clean_rows")
BASE = "/api/modules/telephony/connection"


@pytest.fixture(autouse=True)
def _lan(monkeypatch):
    from backend import connections, netguard

    monkeypatch.setattr(connections, "_resolve_target",
                        lambda host: netguard.check(host, resolve=lambda h: ["192.168.178.1"]))
    yield
    connections.MANAGER.stop_all()


def _cid(client, headers) -> str:
    from backend import connections

    r = client.put(BASE, json={"registrar": "fritz.box", "username": "hydra-telefon", "password": "Sehr-Geheim-42"},
                   headers=headers)
    assert r.status_code == 200
    return connections._row("user:user-owner")["id"]


@pytest.mark.parametrize("info, kind", [
    ({"kind": "assistant"}, "assistant"),
    ({"kind": "greeting"}, "greeting"),
    ({}, "greeting"),
    ({"kind": "irgendwas"}, "greeting"),
])
def test_art_wird_gespeichert_und_geliefert(client, auth_headers, info: dict, kind: str) -> None:
    from backend import calls

    cid = _cid(client, auth_headers)
    calls.record(cid, {"number": "•••567", "result": "answered", **info})
    assert client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"][0]["kind"] == kind


def test_abgelehnt_und_besetzt_haben_keine_art(client, auth_headers) -> None:
    """Nicht angenommene Anrufe hatten weder Ansage noch Gespräch."""
    from backend import calls

    cid = _cid(client, auth_headers)
    for result in ("rejected", "busy"):
        calls.record(cid, {"number": "•••567", "result": result, "kind": "assistant"})
    got = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"]
    assert [c["kind"] for c in got] == ["", ""]


def test_eingehend_assistent_meldet_art() -> None:
    from backend.sip.dispatch import CallDispatcher

    seen: list = []
    d = CallDispatcher(policy=lambda: "Hallo", rtp_ports=(35000, 35010), record=seen.append)

    class Call:
        _assistant: ClassVar[dict] = {"x": 1}
        notes: ClassVar[dict] = {}
        invite = None
        result, codec, rtp_out, rtp_in, turns, call_id = "assistant_end", "PCMA", 1, 1, 2, "c"

    class Ans(Call):
        _assistant = None
        result = "answered"

    d._note = lambda inv, result, **extra: seen.append({"result": result, **extra})
    d._finish(Call())
    d._finish(Ans())
    assert seen[0]["kind"] == "assistant" and seen[1]["kind"] == "greeting"


def test_ausgehend_meldet_art() -> None:
    import socket

    from backend.sip import agent_dial

    seen: list = []

    class Agent:
        status = "registered"
        alive = True
        _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        class _state:
            local = ("127.0.0.1", 1)
            contact = None
            target = ("127.0.0.1", 9)
            user = password = domain = display_name = "x"

        class calls:
            @staticmethod
            def busy():
                return False

            @staticmethod
            def _bind_rtp(ip):
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind(("127.0.0.1", 0))
                return s

            @staticmethod
            def add_outbound(c):
                return True

            @staticmethod
            def finish_outbound(c):
                pass

    started: list = []
    orig = agent_dial.OutboundCall.start
    agent_dial.OutboundCall.start = lambda self: started.append(self)
    try:
        for opts, kind in [({}, "greeting"), ({"assistant": {"cfg": None}}, "assistant")]:
            call = agent_dial.dial(Agent, "0301234567", lambda c: b"", record=seen.append, **opts)
            call.result = "answered"
            call._on_finish(call)
            assert seen[-1]["kind"] == kind
    finally:
        agent_dial.OutboundCall.start = orig
        Agent._sock.close()
