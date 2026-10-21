"""S7: Bluetooth-Ablauf im Vitrine-Dienst – Kopplungsfenster, Aufträge, Stand. BlueZ kommt als Objekt herein
(echt: bt_bluez.Bluez über dbus-fast; Tests: Fake), damit der Ablauf ohne Funk prüfbar ist.

Sicherheit (SPEC S7): Beim Start und nach jedem Fenster ist der Adapter weder pairable noch discoverable, die Suche aus,
der Agent abgemeldet. Gekoppelt wird nur bei offenem Fenster und nur, was die Suche gesehen hat.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Callable

from . import bt_jobs, bt_model

WINDOW_SECONDS = 120
BLUEZ_TIMEOUT = 180       # Netz: stirbt der Dienst bei offenem Fenster, schließt BlueZ selbst (Pairable/Discoverable)
BUSY_FILE = "bt_busy"
log = logging.getLogger("vitrine.bt")


class BluezError(RuntimeError):
    """Fehler aus BlueZ (D-Bus-Fehlername im Text)."""


class Agent:
    """Kopplungs-Agent (KeyboardDisplay). bt_bluez exportiert ihn als org.bluez.Agent1; hier nur der Zustand."""

    def __init__(self, on_change: Callable[[], None]):
        self.passkey: str | None = None
        self._on_change = on_change

    def display_passkey(self, addr: str, passkey: int) -> None:
        self.passkey = f"{int(passkey) % 1_000_000:06d}"
        self._on_change()

    def cancel(self) -> None:
        self.passkey = None
        self._on_change()


class Service:
    def __init__(self, data: Path, bluez, *, clock: Callable[[], float] = time.time,
                 notify: Callable[[str, str], None] | None = None):
        self.data, self.bluez, self.clock = data, bluez, clock
        self.notify = notify or (lambda text, kind: None)
        self.window_until = 0.0
        self.pairing: str | None = None
        self.error: str | None = None
        self.devices: list[dict] = []
        self.adapter: dict | None = None
        self.agent = Agent(self._write)

    # --- Fenster -----------------------------------------------------------------------------------------------
    async def _close(self) -> None:
        for step in (lambda: self.bluez.discovery(False), lambda: self.bluez.set_adapter("Discoverable", False),
                     lambda: self.bluez.set_adapter("Pairable", False), self.bluez.agent_unregister):
            try:
                await step()
            except BluezError as e:                    # schließen versucht immer alle Schritte
                log.warning("Bluetooth schließen: %s", e)
        self.window_until = 0.0
        (self.data / BUSY_FILE).unlink(missing_ok=True)

    async def _open(self) -> None:
        now = self.clock()
        if self.window_until > now:
            return                                      # nicht verlängern
        await self.bluez.set_adapter("Powered", True)
        await self.bluez.set_timeouts(BLUEZ_TIMEOUT)
        await self.bluez.agent_register(self.agent)
        await self.bluez.set_adapter("Pairable", True)
        await self.bluez.set_adapter("Discoverable", True)
        await self.bluez.discovery(True)
        self.window_until = now + WINDOW_SECONDS
        self.error = None
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / BUSY_FILE).write_text(json.dumps({"since": now}))

    # --- Aufträge ----------------------------------------------------------------------------------------------
    async def _pair(self, addr: str) -> None:
        if self.window_until <= self.clock():
            return
        order = bt_model.pair_order(self.devices, addr)
        if not order:
            return
        name = next((r["name"] for r in bt_model.rows(self.devices) if addr in r["addresses"]), addr)
        last = None
        for a in order:                                 # klassisch zuerst, dann LE (21.10.: LE → auth failed 0x05)
            self.pairing, self.agent.passkey = a, None
            self._write()
            try:
                await self.bluez.pair(a)
                await self.bluez.trust(a)
                await self.bluez.connect(a)
            except BluezError as e:
                last = e
                continue
            self.pairing, self.agent.passkey = None, None
            self.notify(f"Bluetooth: {name} gekoppelt", "success")
            await self._close()
            return
        self.pairing, self.agent.passkey = None, None
        self.error = f"{name} nicht gekoppelt: {last}"[:200]

    async def _remove(self, addr: str) -> None:
        name = next((d.get("name") for d in self.devices if d.get("address") == addr), None) or addr
        await self.bluez.remove(addr)
        self.notify(f"Bluetooth: {name} entfernt", "info")

    # --- Takt ----------------------------------------------------------------------------------------------------
    async def start(self) -> None:
        await self._close()
        await self._refresh()
        self._write()

    async def _refresh(self) -> None:
        try:
            self.adapter = await self.bluez.adapter()
            self.devices = await self.bluez.devices_list()
        except BluezError as e:
            self.devices, self.error = [], str(e)[:200]

    async def tick(self) -> None:
        for job in bt_jobs.take(self.data):
            try:
                if job["kind"] == "scan":
                    await self._open()
                    await self._refresh()
                elif job["kind"] == "pair":
                    await self._refresh()
                    await self._pair(job["address"])
                elif job["kind"] == "remove":
                    await self._remove(job["address"])
            except BluezError as e:
                self.error = str(e)[:200]
        if self.window_until and self.window_until <= self.clock():
            await self._close()
        await self._refresh()
        self._write()

    def _write(self) -> None:
        bt_jobs.write_state(self.data, {
            "adapter": {"name": (self.adapter or {}).get("name"), "powered": bool((self.adapter or {}).get("powered"))},
            "window_until": self.window_until,
            "devices": self.devices,
            "pairing": {"address": self.pairing, "passkey": self.agent.passkey} if self.pairing else None,
            "error": self.error,
        }, now=self.clock())
