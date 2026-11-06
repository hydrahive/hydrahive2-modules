"""Erste Stufe der Workspace-Migration: Container bereitmachen, ruhigstellen, `/work` auslesen."""

from __future__ import annotations

import asyncio
import logging
import shutil

from . import container, incus, workspace_mount
from .workspace_read import dev_server, read_work
from .workspace_state import save as _save

logger = logging.getLogger(__name__)


async def _restore(name: str, was_running: bool) -> bool:
    """Ausgangszustand herstellen und BESTÄTIGEN: lief der Container, läuft er samt Dev-Server wieder, sonst ist er aus."""
    running = await container.running_name(name)
    if not was_running:
        if not running:
            return True
        rc, _, _ = await incus.run("stop", name, "--force", timeout=120)
        return rc == 0 and not await container.running_name(name)
    if not running:
        rc, _, _ = await incus.run("start", name, timeout=120)
        if rc != 0 or not await container.running_name(name):
            return False
    return await dev_server(name, "start")


async def abort(project_id: str, name: str, was_running: bool) -> None:
    """Zurück in den Ausgangszustand. Der Marker fällt nur, wenn das bestätigt ist – sonst bleibt er als Hinweis für den
    nächsten Anlauf (der setzt mit dem gespeicherten `was_running` fort)."""
    shutil.rmtree(workspace_mount.staging(project_id), ignore_errors=True)
    try:
        restored = await _restore(name, was_running)
    except Exception:
        logger.exception("Vibe: Wiederherstellung von %s nach Abbruch fehlgeschlagen", name)
        restored = False
    if restored:
        workspace_mount.clear_migration(project_id)
    else:
        logger.error("Vibe: %s nicht sicher wiederhergestellt – Migrationsmarker bleibt stehen", name)


async def begin(project_id: str, name: str, state: dict, before_stop) -> None:
    """Stufe `new`: Container (falls nötig) starten, ruhigstellen, auslesen → `pulled`."""
    was_running = state["was_running"]
    try:
        if before_stop is not None:
            await before_stop()
        if not await container.running_name(name):
            rc, _, _ = await incus.run("start", name, timeout=120)
            if rc != 0 or not await container.running_name(name):
                raise container.VibeError("vibe_container_down")
        await dev_server(name, "stop")
        await read_work(project_id, name)
        state["stage"] = "pulled"
        _save(project_id, state)
    except asyncio.CancelledError:
        await asyncio.shield(abort(project_id, name, was_running))
        raise
    except container.VibeError:
        await abort(project_id, name, was_running)
        raise
    except Exception:
        logger.exception("Vibe: Auslesen von %s fehlgeschlagen", project_id)
        await abort(project_id, name, was_running)
        raise container.VibeError("vibe_workspace_migration_failed") from None
