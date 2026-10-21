"""S7: gemeinsamer Fake für BlueZ und Hilfen der Dienst-Tests (kein Test hier)."""
from __future__ import annotations

import asyncio

from renderer import bt_service

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

    async def set_timeouts(self, seconds):
        self.calls.append(("timeouts", seconds))

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
