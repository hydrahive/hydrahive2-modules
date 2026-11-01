"""Eigene Messung: ping mit fester Argumentliste, Ausgabe lesen."""
from __future__ import annotations

import pytest
from backend import probe

OK = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.

--- 1.1.1.1 ping statistics ---
5 packets transmitted, 4 received, 20% packet loss, time 812ms
rtt min/avg/max/mdev = 14.772/21.115/52.175/7.485 ms
"""
LOST = """PING 9.9.9.9 (9.9.9.9) 56(84) bytes of data.

--- 9.9.9.9 ping statistics ---
5 packets transmitted, 0 received, 100% packet loss, time 4090ms
"""


def test_ausgabe_lesen():
    assert probe.parse_ping(OK) == {"loss": 20.0, "min": 14.772, "avg": 21.115, "max": 52.175, "mdev": 7.485}


def test_alles_verloren():
    assert probe.parse_ping(LOST) == {"loss": 100.0, "min": None, "avg": None, "max": None, "mdev": None}


def test_unlesbar():
    assert probe.parse_ping("ping: connect: Network is unreachable") == {
        "loss": 100.0, "min": None, "avg": None, "max": None, "mdev": None}


@pytest.mark.parametrize("t,ok", [("1.1.1.1", True), ("192.168.178.1", True), ("2606:4700::1111", True),
                                  ("-f", False), ("example.com", False), ("1.1.1.1 -f", False), ("", False)])
def test_nur_ip_adressen(t, ok):
    assert probe.valid_target(t) is ok


async def test_feste_argumente(monkeypatch):
    seen = []

    async def fake(args):
        seen.append(args)
        return OK
    monkeypatch.setattr(probe, "_run", fake)
    r = await probe.ping("1.1.1.1", count=5)
    assert r["loss"] == 20.0
    assert seen == [["ping", "-n", "-q", "-c", "5", "-i", "0.2", "-W", "1", "1.1.1.1"]]


async def test_ungueltiges_ziel_startet_nichts(monkeypatch):
    async def fake(args):
        raise AssertionError("darf nicht laufen")
    monkeypatch.setattr(probe, "_run", fake)
    assert (await probe.ping("-f"))["loss"] is None


async def test_fehler_beim_start(monkeypatch):
    async def fake(args):
        raise OSError("kein ping")
    monkeypatch.setattr(probe, "_run", fake)
    assert (await probe.ping("1.1.1.1"))["loss"] is None


def test_internet_aus_zwei_zielen():
    a = {"loss": 100.0, "min": None, "avg": None, "max": None, "mdev": None}
    b = {"loss": 0.0, "min": 10.0, "avg": 12.0, "max": 20.0, "mdev": 2.0}
    c = {"loss": 20.0, "min": 8.0, "avg": 16.0, "max": 30.0, "mdev": 4.0}
    assert probe.combine([a, b]) == {"loss": 0.0, "min": 10.0, "avg": 12.0, "max": 20.0, "mdev": 2.0}
    assert probe.combine([b, c]) == {"loss": 0.0, "min": 8.0, "avg": 14.0, "max": 30.0, "mdev": 3.0}
    assert probe.combine([a, a])["loss"] == 100.0
    assert probe.combine([{"loss": None}])["loss"] is None
