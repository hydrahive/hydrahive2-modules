"""S7: dünne Schicht auf BlueZ über dbus-fast (System-Bus). Gleiche Methoden wie der Fake in tests/test_bt_service.py.

Nur feste Objektpfade und geprüfte Adressen (bt_model.address) – kein Freitext an D-Bus.
Der Agent (org.bluez.Agent1, KeyboardDisplay) wird beim Öffnen des Fensters exportiert und als Standard angemeldet.
"""
from __future__ import annotations

import asyncio

from dbus_fast import BusType, DBusError, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, method

from . import bt_model
from .bt_service import Agent, BluezError

BLUEZ = "org.bluez"
ADAPTER = "/org/bluez/hci0"
AGENT_PATH = "/org/hydrahive/vitrine/agent"
CAPABILITY = "KeyboardDisplay"
CALL_TIMEOUT, PAIR_TIMEOUT = 5.0, 45.0


def _dev_path(addr: str) -> str:
    ok = bt_model.address(addr)
    if not ok:
        raise BluezError("ungültige Adresse")
    return f"{ADAPTER}/dev_{ok.replace(':', '_')}"


class _Agent1(ServiceInterface):
    """BlueZ ruft diese Methoden während des Koppelns. Tippen auf das Gerät war die Bestätigung."""

    def __init__(self, agent: Agent):
        super().__init__("org.bluez.Agent1")
        self.agent = agent

    @method()
    def Release(self):  # noqa: N802 - D-Bus-Name
        self.agent.cancel()

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):  # noqa: F821, N802
        self.agent.display_passkey(device, passkey)

    @method()
    def RequestConfirmation(self, device: "o", passkey: "u"):  # noqa: F821, N802
        self.agent.display_passkey(device, passkey)            # Zahlenvergleich: anzeigen und annehmen

    @method()
    def RequestAuthorization(self, device: "o"):  # noqa: F821, N802
        return

    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):  # noqa: F821, N802
        return

    @method()
    def Cancel(self):  # noqa: N802
        self.agent.cancel()


class Bluez:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self._agent_iface: _Agent1 | None = None

    @classmethod
    async def open(cls) -> "Bluez":
        try:
            return cls(await MessageBus(bus_type=BusType.SYSTEM).connect())
        except (OSError, DBusError) as e:
            raise BluezError(f"System-Bus nicht erreichbar: {e}") from e

    async def _iface(self, path: str, name: str):
        try:
            intro = await asyncio.wait_for(self.bus.introspect(BLUEZ, path), CALL_TIMEOUT)
            return self.bus.get_proxy_object(BLUEZ, path, intro).get_interface(name)
        except (DBusError, asyncio.TimeoutError) as e:
            raise BluezError(getattr(e, "type", None) or str(e) or "BlueZ antwortet nicht") from e

    async def _call(self, path: str, iface: str, name: str, *args, timeout: float = CALL_TIMEOUT):
        obj = await self._iface(path, iface)
        try:
            return await asyncio.wait_for(getattr(obj, f"call_{name}")(*args), timeout)
        except DBusError as e:
            raise BluezError(e.type or str(e)) from e
        except asyncio.TimeoutError as e:
            raise BluezError(f"{name}: Zeit abgelaufen") from e

    async def adapter(self) -> dict:
        props = await self._call(ADAPTER, "org.freedesktop.DBus.Properties", "get_all", "org.bluez.Adapter1")
        return {"name": props.get("Alias", props.get("Name", Variant("s", ""))).value,
                "powered": bool(props.get("Powered", Variant("b", False)).value)}

    async def set_adapter(self, prop: str, value: bool) -> None:
        if prop not in ("Powered", "Pairable", "Discoverable"):
            raise BluezError("unbekannte Eigenschaft")
        await self._call(ADAPTER, "org.freedesktop.DBus.Properties", "set", "org.bluez.Adapter1", prop,
                         Variant("b", bool(value)))

    async def set_timeouts(self, seconds: int) -> None:
        for prop in ("PairableTimeout", "DiscoverableTimeout"):
            await self._call(ADAPTER, "org.freedesktop.DBus.Properties", "set", "org.bluez.Adapter1", prop,
                             Variant("u", int(seconds)))

    async def discovery(self, on: bool) -> None:
        try:
            await self._call(ADAPTER, "org.bluez.Adapter1", "start_discovery" if on else "stop_discovery")
        except BluezError as e:
            if not on and ("NotReady" in str(e) or "Failed" in str(e)):
                return                                           # war schon aus
            if on and "InProgress" in str(e):
                return
            raise

    async def agent_register(self, agent: Agent) -> None:
        if self._agent_iface is None:
            self._agent_iface = _Agent1(agent)
            self.bus.export(AGENT_PATH, self._agent_iface)
        await self._call("/org/bluez", "org.bluez.AgentManager1", "register_agent", AGENT_PATH, CAPABILITY)
        await self._call("/org/bluez", "org.bluez.AgentManager1", "request_default_agent", AGENT_PATH)

    async def agent_unregister(self) -> None:
        if self._agent_iface is None:
            return
        try:
            await self._call("/org/bluez", "org.bluez.AgentManager1", "unregister_agent", AGENT_PATH)
        except BluezError:
            pass                                                 # war nicht (mehr) angemeldet
        self.bus.unexport(AGENT_PATH)
        self._agent_iface = None

    async def devices_list(self) -> list[dict]:
        om = await self._call("/", "org.freedesktop.DBus.ObjectManager", "get_managed_objects")
        out = []
        for path, ifaces in om.items():
            d = ifaces.get("org.bluez.Device1")
            if not d or not path.startswith(ADAPTER + "/"):
                continue
            g = lambda k, default=None: d[k].value if k in d else default  # noqa: E731
            addr = bt_model.address(g("Address"))
            if not addr:
                continue
            out.append({"address": addr, "address_type": g("AddressType"), "name": g("Name"), "rssi": g("RSSI"),
                        "icon": g("Icon"), "paired": bool(g("Paired", False)), "connected": bool(g("Connected", False)),
                        # klassisch = hat eine Geräteklasse (BR/EDR, z. B. Rapoo BT3.0: 0x000540); LE-Geräte haben keine
                        "le": g("Class") is None})
        return out

    async def pair(self, addr: str) -> None:
        await self._call(_dev_path(addr), "org.bluez.Device1", "pair", timeout=PAIR_TIMEOUT)

    async def trust(self, addr: str) -> None:
        await self._call(_dev_path(addr), "org.freedesktop.DBus.Properties", "set", "org.bluez.Device1", "Trusted",
                         Variant("b", True))

    async def connect(self, addr: str) -> None:
        await self._call(_dev_path(addr), "org.bluez.Device1", "connect", timeout=15.0)

    async def remove(self, addr: str) -> None:
        await self._call(ADAPTER, "org.bluez.Adapter1", "remove_device", _dev_path(addr))
