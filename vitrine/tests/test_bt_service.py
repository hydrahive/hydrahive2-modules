"""S7: Ablauf im Dienst mit einem Fake-BlueZ – Fenster, Aufräumen, Koppeln (klassisch zuerst), Code, Meldungen."""
from __future__ import annotations

import asyncio

import pytest

from renderer import bt_jobs, bt_service

A3, A4 = "B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"


class FakeBluez:
    """Spielt BlueZ nach: Eigenschaften, Suche, Agent, pair/trust/connect/remove. Protokolliert alle Aufrufe."""

    def __init__(self, devices=None, *, fail_pair=()):
        self.calls: list[tuple] = []
        self.props = {"Powered": True, "Pairable": True, "Discoverable": True}   # „schmutziger“ Start
        self.discovering = True
        self.agent = False
        self.fail_pair = set(fail_pair)
        self.devices = {d["address"]: d for d in (devices or [])}
        self.on_pair = None                                       # Hook: z. B. Code anzeigen während des Koppelns

    async def adapter(self):
        return {"name": "hydrahive-master", "powered": self.props["Powered"], **self.props}

    async def set_adapter(self, prop, value):
        self.calls.append(("set", prop, value))
        self.props[prop] = value

    async def discovery(self, on):
        self.calls.append(("discovery", on))
        self.discovering = on

    async def agent_register(self, agent):
        self.calls.append(("agent", True))
        self.agent = agent

    async def agent_unregister(self):
        self.calls.append(("agent", False))
        self.agent = False

    async def devices_list(self):
        return list(self.devices.values())

    async def pair(self, addr):
        self.calls.append(("pair", addr))
        if self.on_pair:
            await self.on_pair(addr)
        if addr in self.fail_pair:
            raise bt_service.BluezError("org.bluez.Error.AuthenticationFailed")
        self.devices[addr]["paired"] = True

    async def trust(self, addr):
        self.calls.append(("trust", addr))

    async def connect(self, addr):
        self.calls.append(("connect", addr))
        self.devices[addr]["connected"] = True

    async def remove(self, addr):
        self.calls.append(("remove", addr))
        self.devices.pop(addr, None)


RAPOO = [{"address": A3, "name": "RAPOO BT3.0 KB", "rssi": -62, "icon": "input-keyboard", "le": False},
         {"address": A4, "name": "RAPOO BT4.0 KB", "rssi": -58, "icon": "input-keyboard", "le": True}]


def svc(tmp_path, fake, now=1000.0):
    clock = {"t": now}
    s = bt_service.Service(tmp_path, fake, clock=lambda: clock["t"], notify=lambda text, kind: s.notes.append((text, kind)))
    s.notes = []
    return s, clock


def run(coro):
    return asyncio.run(coro)


def test_start_schliesst_alles(tmp_path):
    fake = FakeBluez()
    s, _ = svc(tmp_path, fake)
    run(s.start())
    assert fake.props["Pairable"] is False and fake.props["Discoverable"] is False
    assert fake.discovering is False and fake.agent is False
    assert bt_jobs.read_state(tmp_path)["window_until"] == 0


def test_fenster_oeffnen_und_nach_120s_schliessen(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert ("set", "Powered", True) in fake.calls and ("set", "Pairable", True) in fake.calls
    assert ("set", "Discoverable", True) in fake.calls and fake.discovering and fake.agent
    st = bt_jobs.read_state(tmp_path)
    assert st["window_until"] == clock["t"] + bt_service.WINDOW_SECONDS == 1120.0
    assert {d["address"] for d in st["devices"]} == {A3, A4}
    clock["t"] += bt_service.WINDOW_SECONDS - 1
    run(s.tick())
    assert fake.discovering is True                                      # noch offen
    clock["t"] += 2
    run(s.tick())
    assert fake.props["Pairable"] is False and fake.props["Discoverable"] is False
    assert fake.discovering is False and fake.agent is False
    assert bt_jobs.read_state(tmp_path)["window_until"] == 0


def test_zweiter_scan_verlaengert_nicht(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    clock["t"] += 60
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert bt_jobs.read_state(tmp_path)["window_until"] == 1120.0


def test_koppeln_klassisch_zuerst_dann_trust_connect_meldung(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", A4, now=clock["t"])                   # angetippt wurde die LE-Adresse
    run(s.tick())
    assert [c for c in fake.calls if c[0] in ("pair", "trust", "connect")] == [
        ("pair", A3), ("trust", A3), ("connect", A3)]
    assert s.notes == [("Bluetooth: RAPOO KB gekoppelt", "success")]
    assert fake.props["Pairable"] is False                               # nach Erfolg sofort zu


def test_klassisch_scheitert_dann_le(tmp_path):
    fake = FakeBluez(RAPOO, fail_pair={A3})
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    assert [c for c in fake.calls if c[0] == "pair"] == [("pair", A3), ("pair", A4)]
    assert ("connect", A4) in fake.calls


def test_beide_scheitern_fehler_im_stand_fenster_bleibt_offen(tmp_path):
    fake = FakeBluez(RAPOO, fail_pair={A3, A4})
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    st = bt_jobs.read_state(tmp_path)
    assert "nicht gekoppelt" in st["error"] and st["pairing"] is None
    assert st["window_until"] > clock["t"] and s.notes == []             # nochmal versuchen möglich


def test_koppeln_bei_geschlossenem_fenster_tut_nichts(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    assert not [c for c in fake.calls if c[0] == "pair"]


def test_code_erscheint_waehrend_des_koppelns_und_verschwindet(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    seen = {}

    async def show(addr):
        s.agent.display_passkey(addr, 123456)                             # BlueZ ruft DisplayPasskey am Agenten
        seen["state"] = bt_jobs.read_state(tmp_path)

    fake.on_pair = show
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    bt_jobs.put(tmp_path, "pair", A3, now=clock["t"])
    run(s.tick())
    assert seen["state"]["pairing"] == {"address": A3, "passkey": "123456"}
    assert bt_jobs.read_state(tmp_path)["pairing"] is None


def test_entfernen_auch_ohne_fenster_und_meldung(tmp_path):
    fake = FakeBluez([dict(RAPOO[0], paired=True)])
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "remove", A3, now=clock["t"])
    run(s.tick())
    assert ("remove", A3) in fake.calls and s.notes == [("Bluetooth: RAPOO BT3.0 KB entfernt", "info")]


def test_bluez_fehler_beim_lesen_stoppt_nicht(tmp_path):
    fake = FakeBluez(RAPOO)

    async def kaputt():
        raise bt_service.BluezError("org.freedesktop.DBus.Error.ServiceUnknown")

    fake.devices_list = kaputt
    s, clock = svc(tmp_path, fake)
    run(s.start())
    run(s.tick())
    st = bt_jobs.read_state(tmp_path)
    assert st["devices"] == [] and "ServiceUnknown" in st["error"]


@pytest.mark.parametrize("busy", [True, False])
def test_busy_datei_nur_bei_offenem_fenster(tmp_path, busy):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    if busy:
        bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert (tmp_path / bt_service.BUSY_FILE).exists() is busy


def test_ungesehenes_geraet_wird_nicht_gekoppelt(tmp_path):
    """Auch wenn ein Auftrag am Backend vorbei in bt/inbox landet: nur Geräte, die die Suche sieht."""
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    fake.calls.clear()
    bt_jobs.put(tmp_path, "pair", "AA:AA:AA:AA:AA:AA", now=clock["t"])
    run(s.tick())
    assert not [c for c in fake.calls if c[0] == "pair"]


def test_busy_datei_verschwindet_wenn_fenster_zu(tmp_path):
    fake = FakeBluez(RAPOO)
    s, clock = svc(tmp_path, fake)
    run(s.start())
    bt_jobs.put(tmp_path, "scan", now=clock["t"])
    run(s.tick())
    assert (tmp_path / bt_service.BUSY_FILE).exists()
    clock["t"] += bt_service.WINDOW_SECONDS + 1
    run(s.tick())
    assert not (tmp_path / bt_service.BUSY_FILE).exists()


def test_start_raeumt_alte_busy_datei_weg(tmp_path):
    (tmp_path / bt_service.BUSY_FILE).write_text('{"since": 1}')
    s, _ = svc(tmp_path, FakeBluez())
    run(s.start())
    assert not (tmp_path / bt_service.BUSY_FILE).exists()
