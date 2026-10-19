"""Warteschlange für Filme (Spec „7c im Detail“): ein Film zur Zeit auf dem ganzen Server, Reihenfolge der Klicks.

Eigene FIFO statt Semaphor (dessen Reihenfolge ist nicht garantiert). `enter` reiht beim Klick ein (höchstens
MAX_PER_PROJECT je Projekt), `turn` wartet im Auftrags-Thread, bis der Film dran ist, und gibt den Platz am Ende frei.
Wer beim Warten abbricht, verlässt die Schlange sofort.
"""
from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from . import jobs
from ._store import new_id

MAX_PER_PROJECT = 5
POLL = 0.2                                   # so oft prüft ein wartender Film, ob er abgebrochen wurde

_cond = threading.Condition()
_line: list[tuple[str, str]] = []            # (Ticket, Projekt); vorne = läuft bzw. ist als Nächstes dran


class QueueFull(RuntimeError):
    """Schon MAX_PER_PROJECT Filme dieses Projekts in der Schlange."""


def pending(pid: str) -> int:
    with _cond:
        return sum(1 for _, p in _line if p == pid)


def enter(pid: str) -> tuple[str, int]:
    """Einreihen. Gibt (Ticket, Platz) zurück; Platz 1 = sofort dran."""
    with _cond:
        if sum(1 for _, p in _line if p == pid) >= MAX_PER_PROJECT:
            raise QueueFull()
        ticket = new_id()
        _line.append((ticket, pid))
        return ticket, len(_line)


def leave(ticket: str) -> None:
    with _cond:
        _line[:] = [x for x in _line if x[0] != ticket]
        _cond.notify_all()


@contextmanager
def turn(ticket: str, progress) -> Iterator[None]:
    """Warten, bis das Ticket vorne steht (Status „queued“), dann „running“. Abbrechen beim Warten → jobs.Cancelled."""
    try:
        with _cond:
            while not (_line and _line[0][0] == ticket):
                if progress.cancelled():
                    raise jobs.Cancelled()
                _cond.wait(POLL)
        progress.job["status"] = "running"
        progress.set()
        yield
    finally:
        leave(ticket)
