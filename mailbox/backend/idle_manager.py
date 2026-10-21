"""Aufseher für IDLE-Threads (PLAN-M2 Schritt 9). Ein Modul-Job ruft reconcile() regelmäßig auf:

- je Konto genau ein Thread (daemon – blockiert den Shutdown nie; Stopp-Signal beendet ihn sauber mit DONE)
- gelöschte Konten → Thread beenden; geänderte Zugangsdaten → neu starten
- Server ohne IDLE → merken und nicht im Takt neu probieren (bis die Zugangsdaten sich ändern)
- HH_MAILBOX_IDLE=0 schaltet IDLE ab (der 5-Minuten-Abgleich bleibt)
Neue Mail → Abgleich im Event-Loop (sync_job._run sperrt je Konto, kein Doppellauf mit dem Takt-Job).
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading

from . import accounts, idle, sync_job

log = logging.getLogger("hydrahive.modules.mailbox")
_KEY = ("imap_host", "imap_port", "imap_tls", "username", "address")


def enabled() -> bool:
    return os.environ.get("HH_MAILBOX_IDLE", "1").strip() not in ("0", "false", "no", "off")


def _fingerprint(acc: dict) -> tuple:
    return tuple(str(acc.get(k, "")) for k in _KEY)


def _trigger(loop: asyncio.AbstractEventLoop):
    def fire(acc: dict) -> None:
        # Kontodaten des Threads genügen: ändern sie sich, startet reconcile() den Thread mit den neuen neu
        asyncio.run_coroutine_threadsafe(sync_job._run(acc), loop)
    return fire


class Manager:
    def __init__(self):
        self._threads: dict[str, tuple[threading.Thread, threading.Event, tuple]] = {}
        self._unsupported: dict[str, tuple] = {}
        self._lock = threading.Lock()

    def running(self) -> list[str]:
        with self._lock:
            return sorted(aid for aid, (t, _, _) in self._threads.items() if t.is_alive())

    def _start(self, acc: dict, trigger) -> None:
        stop, fp = threading.Event(), _fingerprint(acc)

        def run():
            try:
                r = idle.watch(acc, stop, trigger, open_conn=sync_job._open, password_of=accounts.password_of)
            except Exception as e:  # noqa: BLE001 - ein Konto darf die anderen nie stören
                log.warning("Mailbox-IDLE %s beendet: %s", acc["id"], str(e)[:200])
                r = "error"
            with self._lock:
                if r == "unsupported":
                    self._unsupported[acc["id"]] = fp
                cur = self._threads.get(acc["id"])
                if cur and cur[1] is stop:
                    del self._threads[acc["id"]]
        t = threading.Thread(target=run, name=f"mailbox-idle-{acc['id']}", daemon=True)
        self._threads[acc["id"]] = (t, stop, fp)
        t.start()

    def reconcile(self, accs: list[dict], trigger=None) -> None:
        trigger = trigger or (lambda acc: None)
        want = {a["id"]: a for a in accs} if enabled() else {}
        with self._lock:
            for aid, (t, stop, fp) in list(self._threads.items()):
                if aid not in want or _fingerprint(want[aid]) != fp:
                    stop.set()
                    del self._threads[aid]
            for aid, acc in want.items():
                if aid in self._threads:
                    continue
                if self._unsupported.get(aid) == _fingerprint(acc):
                    continue
                self._unsupported.pop(aid, None)
                self._start(acc, trigger)

    def stop_all(self) -> None:
        with self._lock:
            for _, stop, _ in self._threads.values():
                stop.set()
            self._threads.clear()


MANAGER = Manager()


async def job() -> None:
    """Modul-Job (jede Minute): IDLE-Threads zu den Konten passend halten."""
    MANAGER.reconcile(accounts.all_accounts(), _trigger(asyncio.get_running_loop()))
