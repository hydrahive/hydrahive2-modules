"""S7: Bluetooth läuft im Vitrine-Dienst in einem eigenen Thread mit asyncio-Schleife. Fehler dort stoppen das Display nie.

Ohne dbus-fast oder ohne BlueZ (kein Adapter, Bus weg) wartet der Thread und versucht es alle RETRY_SECONDS neu.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path

from . import inbox

TICK_SECONDS, RETRY_SECONDS = 1.0, 30.0
log = logging.getLogger("vitrine.bt")


def _notifier(data: Path):
    def notify(text: str, kind: str) -> None:
        try:
            inbox.post(data, text, kind=kind, source="bluetooth")
        except (inbox.InboxError, OSError) as e:
            log.warning("Bluetooth-Meldung nicht abgelegt: %s", e)
    return notify


async def _loop(data: Path, stop: threading.Event, *, opener=None, tick=TICK_SECONDS, retry=RETRY_SECONDS) -> None:
    from .bt_service import BluezError, Service
    if opener is None:
        from .bt_bluez import Bluez
        opener = Bluez.open
    while not stop.is_set():
        try:
            svc = Service(data, await opener(), notify=_notifier(data))
            await svc.start()
            while not stop.is_set():
                await svc.tick()
                await asyncio.sleep(tick)
            return
        except (BluezError, OSError) as e:
            log.warning("Bluetooth nicht verfügbar: %s – neuer Versuch in %.0f s", e, retry)
        except Exception:                                  # noqa: BLE001 - Display darf nie mitsterben
            log.exception("Bluetooth-Schleife abgebrochen – neuer Versuch in %.0f s", retry)
        await asyncio.sleep(retry)


def start(data: Path) -> threading.Event | None:
    """Startet den Bluetooth-Thread (Daemon). Gibt das Stopp-Signal zurück; None, wenn dbus-fast fehlt."""
    try:
        import dbus_fast  # noqa: F401
    except ImportError:
        log.info("dbus-fast fehlt – Bluetooth aus")
        return None
    stop = threading.Event()
    threading.Thread(target=lambda: asyncio.run(_loop(data, stop)), name="vitrine-bt", daemon=True).start()
    return stop
