"""Serialisierung und Ruhigstellung für Workspace-Mount, Migration und Löschen eines Vibe-Projekts.

- `project()`: je Projekt genau EIN Vorgang (asyncio-Lock je Ereignisschleife + `flock` auf einer Datei, damit auch ein
  zweiter Serverprozess nicht dazwischenfunkt). Ein Konflikt zwischen Prozessen meldet `vibe_busy`. Die Sperrdatei wird
  nur unter der Sperre entfernt (`discard`); wer sie öffnet, prüft nach dem `flock`, dass der Name noch auf dieselbe
  Inode zeigt, sonst versucht er es mit der neuen Datei erneut (sonst gäbe es zwei Halter auf zwei Inodes).
- `quiesced()`: hält den Session-Lauf-Guard des Kerns für ALLE Sitzungen, die zum Projekt gehören – die des
  Projekt-Agenten UND jede Sitzung (auch von Spezialisten), deren `project_id` auf das Projekt zeigt. Solange er
  gehalten wird, kann kein Lauf starten (der Kern meldet „läuft bereits“); ein bereits laufender Lauf verhindert die
  Ruhigstellung. `refresh()` erfasst neu entstandene Sitzungen und wird vor dem Auslesen UND direkt vor dem Stoppen
  gerufen; die Guards bleiben bis nach dem Stopp gehalten. Grenze: der Guard des Kerns gilt nur innerhalb EINES
  Serverprozesses (concurrency.py: „Single-Process-Schutz“).
"""

from __future__ import annotations

import asyncio
import fcntl
import os
import weakref
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from . import container

_LOCKS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # Ereignisschleife → {projekt: Lock}
_RETRIES = 5


def _lock_file(project_id: str) -> Path:
    from hydrahive.settings import settings

    container.name_for(project_id)  # validiert die ID vor jeder Pfadbildung
    root = settings.data_dir / "vibe" / "workspace-locks"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / f"{project_id}.lock"


def _async_lock(project_id: str) -> asyncio.Lock:
    per_loop = _LOCKS.setdefault(asyncio.get_running_loop(), {})
    return per_loop.setdefault(project_id, asyncio.Lock())


def _acquire(path: Path) -> int:
    """Datei öffnen und sperren; zeigt der Name danach auf eine andere Inode, war die Sperre wertlos → erneut."""
    for _ in range(_RETRIES):
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise container.VibeError("vibe_busy") from None
        try:
            same = os.fstat(fd).st_ino == os.stat(path).st_ino
        except OSError:
            same = False
        if same:
            return fd
        os.close(fd)
    raise container.VibeError("vibe_busy")


@asynccontextmanager
async def project(project_id: str) -> AsyncIterator[None]:
    """Exklusiver Zugriff auf Mount/Migration/Löschen eines Projekts."""
    path = _lock_file(project_id)
    async with _async_lock(project_id):
        fd = _acquire(path)
        try:
            yield
        finally:
            os.close(fd)  # gibt auch den flock frei


def discard(project_id: str) -> None:
    """Sperrdatei entfernen – nur aufrufen, solange `project()` für dieses Projekt gehalten wird."""
    _lock_file(project_id).unlink(missing_ok=True)


def _session_rows() -> list[tuple[str, str, str | None]]:
    """(Sitzungs-ID, Agent, Projekt) aller Sitzungen – ohne Mengenlimit."""
    from hydrahive.db.connection import db

    with db() as conn:
        rows = conn.execute("SELECT id, agent_id, project_id FROM sessions").fetchall()
    return [(r["id"], r["agent_id"], r["project_id"]) for r in rows]


def _session_ids(agent_id: str, project_id: str) -> set[str]:
    return {
        sid for sid, agent, project in _session_rows()
        if (agent_id and agent == agent_id) or project == project_id
    }


class Quiet:
    """Gehaltene Session-Guards eines Projekt-Agenten."""

    def __init__(self, agent_id: str, project_id: str, stack: AsyncExitStack) -> None:
        self.agent_id = agent_id
        self.project_id = project_id
        self.stack = stack
        self.held: set[str] = set()

    async def refresh(self) -> None:
        """Neu entstandene Sitzungen erfassen; läuft eine, oder läuft ein entkoppelter Run-Task: `vibe_busy`."""
        from hydrahive.runner import concurrency

        while True:
            fresh = _session_ids(self.agent_id, self.project_id) - self.held
            if not fresh:
                break
            for sid in sorted(fresh):
                try:
                    await self.stack.enter_async_context(concurrency.session_run_guard(sid))
                except concurrency.SessionAlreadyRunning:
                    raise container.VibeError("vibe_busy") from None
                self.held.add(sid)
        for sid in self.held:  # ein entkoppelter Run-Task ohne Guard zählt ebenfalls als laufend
            task = concurrency.get_task(sid)
            if task is not None and not task.done():
                raise container.VibeError("vibe_busy")


@asynccontextmanager
async def quiesced(agent_id: str, project_id: str, *, stop_first=None) -> AsyncIterator[Quiet]:
    """Kein Lauf des Projekts (auch kein Spezialist) kann laufen oder starten, solange der Block offen ist.

    `stop_first` (async, optional) läuft VOR dem Greifen der Guards – so kann das Löschen laufende Läufe erst abbrechen
    und danach festhalten. Ohne es meldet ein laufender Lauf sofort `vibe_busy` (Migration)."""
    async with AsyncExitStack() as stack:
        quiet = Quiet(agent_id, project_id, stack)
        if stop_first is not None:
            await stop_first()
        await quiet.refresh()
        yield quiet
