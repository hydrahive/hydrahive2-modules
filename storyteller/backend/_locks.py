"""Sperre je Buch: alle Änderungen an einem Buch laufen nacheinander (Fix 0.6.1).

Ohne Sperre konnten zwei gleichzeitige Anfragen beide die Versionsprüfung bestehen (lesen → prüfen →
schreiben), und gleichzeitige Gliederungs-Änderungen (Szene/Kapitel anlegen, löschen) überschrieben sich
gegenseitig. Synchrone Routen laufen bei FastAPI im Threadpool, der Ghostwriter-Lauf im Event-Loop – beide
gehen durch dieselben Funktionen, also schützt ein ``threading.RLock`` beide Wege.

ANNAHME: ein Server-Prozess (uvicorn ohne ``--workers``; so läuft HydraHive). Bei mehreren Prozessen
müsste hier eine Datei-Sperre (``fcntl.flock`` auf ``<buch>/.lock``) her. Dasselbe gilt für die
Prozess-Zustände ``ai._busy``/``ai._rate`` und ``run_engine._cancelled``.
RLock, weil Änderungen geschachtelt aufrufen (Vorschlag übernehmen → Szene speichern).
"""
from __future__ import annotations

import functools
import threading
from typing import Any, Callable, TypeVar

_guard = threading.Lock()
_locks: dict[tuple[str, str], threading.RLock] = {}
F = TypeVar("F", bound=Callable[..., Any])


def book_lock(project_id: str, book_id: str) -> threading.RLock:
    key = (project_id, book_id)
    with _guard:
        lock = _locks.get(key)
        if lock is None:
            lock = _locks[key] = threading.RLock()
        return lock


def locked(fn: F) -> F:
    """Dekorator für Änderungen mit Signatur ``fn(project_id, book_id, ...)``."""
    @functools.wraps(fn)
    def wrapper(project_id: str, book_id: str, *args: Any, **kwargs: Any) -> Any:
        with book_lock(project_id, book_id):
            return fn(project_id, book_id, *args, **kwargs)
    return wrapper  # type: ignore[return-value]
