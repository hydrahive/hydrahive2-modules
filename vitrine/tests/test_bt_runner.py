"""S7: Bluetooth-Thread – Fehler beim Öffnen führen zu neuem Versuch, nie zum Absturz; Meldungen landen im Verlauf."""
from __future__ import annotations

import asyncio
import threading

from renderer import bt_runner, bt_service, inbox


def test_neuer_versuch_nach_fehler_und_dann_lauf(tmp_path):
    from test_bt_service import FakeBluez
    stop, tries = threading.Event(), []
    fake = FakeBluez()

    async def opener():
        tries.append(1)
        if len(tries) == 1:
            raise bt_service.BluezError("org.freedesktop.DBus.Error.ServiceUnknown")
        if len(tries) == 2:
            raise RuntimeError("unerwartet")
        asyncio.get_running_loop().call_later(0.05, stop.set)
        return fake

    asyncio.run(asyncio.wait_for(bt_runner._loop(tmp_path, stop, opener=opener, tick=0.01, retry=0.01), 5))
    assert len(tries) == 3
    assert ("set", "Pairable", False) in fake.calls, "Start schließt alles"
    assert (tmp_path / "bt" / "state.json").exists()


def test_meldung_landet_im_verlauf(tmp_path):
    bt_runner._notifier(tmp_path)("Bluetooth: RAPOO BT3.0 KB gekoppelt", "success")
    msgs = inbox.visible(tmp_path)
    assert msgs and msgs[0]["text"] == "Bluetooth: RAPOO BT3.0 KB gekoppelt" and msgs[0]["kind"] == "success"


def test_ohne_dbus_fast_kein_thread(tmp_path, monkeypatch):
    import builtins
    real = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "dbus_fast":
            raise ImportError(name)
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert bt_runner.start(tmp_path) is None
