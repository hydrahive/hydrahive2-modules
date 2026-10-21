"""S7: bt_bluez ohne Funk – Objektpfad nur aus geprüfter Adresse, Eigenschaften nur aus fester Liste."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("dbus_fast")
from renderer import bt_bluez as b  # noqa: E402
from renderer.bt_service import BluezError  # noqa: E402


def test_objektpfad_nur_aus_gueltiger_adresse():
    assert b._dev_path("b4:ee:25:ed:70:7f") == "/org/bluez/hci0/dev_B4_EE_25_ED_70_7F"
    for bad in ("../../x", "B4:EE:25:ED:70", "", "B4_EE_25_ED_70_7F"):
        with pytest.raises(BluezError):
            b._dev_path(bad)


def test_nur_feste_adapter_eigenschaften():
    bz = b.Bluez(bus=None)
    with pytest.raises(BluezError):
        asyncio.run(bz.set_adapter("Alias", True))


def test_agent_code_sechsstellig_und_abbruch():
    from renderer.bt_service import Agent
    changes = []
    a = Agent(lambda: changes.append(1))
    a.display_passkey("/org/bluez/hci0/dev_X", 42)
    assert a.passkey == "000042" and len(changes) == 1
    a.display_passkey("/org/bluez/hci0/dev_X", 1_234_567)        # BlueZ liefert 0…999999; mehr wird abgeschnitten
    assert a.passkey == "234567"
    a.cancel()
    assert a.passkey is None and len(changes) == 3


def test_agent_schnittstelle_hat_die_bluez_methoden():
    from renderer.bt_service import Agent
    iface = b._Agent1(Agent(lambda: None))
    names = {m.name for m in iface._ServiceInterface__methods} if hasattr(iface, "_ServiceInterface__methods") else set()
    if not names:                                                   # interne Namen je nach dbus-fast-Version
        names = {n for n in dir(iface) if n[0].isupper()}
    assert {"Release", "DisplayPasskey", "RequestConfirmation", "RequestAuthorization", "AuthorizeService",
            "Cancel"} <= names
