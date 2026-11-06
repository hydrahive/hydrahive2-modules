"""Crash-feste Migration des internen Container-`/work` in den Hostworkspace.

Der Inhalt von `/work` kommt als tar-Strom aus dem (ruhiggestellten) Container, wird zweimal gezogen und verglichen
und erst dann sicher auf dem Host entpackt (`workspace_tar`). Danach wird der Container vollständig gestoppt. Das
bisherige interne `/work` wird niemals verändert oder gelöscht; nach dem Mount bleibt es als verdeckte Rückfallebene
auf der Container-Rootdisk erhalten.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import container, incus, workspace_acl, workspace_mount
from .workspace_begin import abort as _abort
from .workspace_begin import begin as _begin
from .workspace_state import open_group_bits as _open_group_bits
from .workspace_state import save as _save

STAGES = ("new", "pulled", "stopped", "published", "mounted")


def _load(project_id: str, was_running: bool) -> dict:
    marker = workspace_mount.marker(project_id)
    if not marker.exists():
        state = {"stage": "new", "was_running": bool(was_running)}
        _save(project_id, state)
        return state
    try:
        state = json.loads(marker.read_text(encoding="utf-8"))
        if state.get("stage") not in STAGES or not isinstance(
            state.get("was_running"), bool
        ):
            raise ValueError
        return state
    except (OSError, ValueError, json.JSONDecodeError, AttributeError):
        raise container.VibeError("vibe_workspace_migration_failed") from None


def _has_data(path: Path) -> bool:
    return path.is_dir() and next(path.iterdir(), None) is not None


def _remove_empty(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        raise container.VibeError("vibe_workspace_conflict") from None


async def _stop_and_isolate(name: str) -> None:
    if await container.running_name(name):
        rc, _, _ = await incus.run("stop", name, "--force", timeout=120)
        if rc != 0 or await container.running_name(name):
            raise container.VibeError("vibe_container_down")
    rc, _, _ = await incus.run("config", "set", name, "security.idmap.isolated", "true")
    if rc != 0:
        raise container.VibeError("vibe_workspace_unavailable")


def _publish(path: Path, source: Path, state: dict) -> None:
    """Gezogenen Baum atomar an die Stelle des leeren Hostworkspaces setzen.

    Vor dem `os.replace` wird die Inode des gezogenen Baums im Marker festgehalten. Nach einem Absturz gilt „Quelle
    fehlt + Host befüllt“ NUR dann als erfolgreicher Publish, wenn der Host genau diese Inode trägt – nie allein wegen
    irgendwelcher Dateien im Hostworkspace.
    """
    source_exists = source.is_dir()
    if source_exists:
        host_has = _has_data(path)
        if host_has and _has_data(source):
            raise container.VibeError("vibe_workspace_conflict")
        if not host_has:
            stat_info = source.stat()
            state["source_dev"], state["source_ino"] = stat_info.st_dev, stat_info.st_ino
            state["stage"] = "pulled"
            _save(state["_project_id"], state)
            _remove_empty(path)
            os.replace(source, path)  # gleicher data_dir-Dateibaum: atomar
    else:
        proof = (state.get("source_dev"), state.get("source_ino"))
        have = (path.stat().st_dev, path.stat().st_ino) if path.is_dir() else None
        if proof[0] is None or have is None or have != proof:
            raise container.VibeError("vibe_workspace_migration_failed")
    from hydrahive.projects._paths import WORKSPACE_DIR_MODE

    os.chmod(path, WORKSPACE_DIR_MODE)
    _open_group_bits(path)


async def migrate(project_id: str, path: Path, *, was_running: bool, before_stop=None) -> None:
    """Migration ab gespeichertem Stage fortsetzen; jeder Stage ist wiederholbar. `before_stop` (async) wird vor dem
    Auslesen UND direkt vor dem Stoppen des Containers gerufen und wirft `vibe_busy`, wenn ein Agentenlauf läuft."""
    name = container.name_for(project_id)
    state = _load(project_id, was_running)
    stage = state["stage"]

    if stage == "new":
        await _begin(project_id, name, state, before_stop)
        stage = "pulled"

    source = workspace_mount.staging(project_id) / "work"
    if stage == "pulled":
        try:
            if before_stop is not None:
                await before_stop()  # ein Lauf, der seit dem Auslesen startete, würde Daten verlieren
        except container.VibeError:
            await _abort(project_id, name, state["was_running"])
            raise
        await _stop_and_isolate(name)
        state["stage"] = stage = "stopped"
        _save(project_id, state)

    if stage == "stopped":
        state["_project_id"] = project_id
        try:
            _publish(path, source, state)
        except container.VibeError as exc:
            if exc.code == "vibe_workspace_conflict":
                workspace_mount.clear_migration(project_id)
                if state["was_running"]:
                    await container.start(project_id)
            raise
        state.pop("_project_id", None)
        state["stage"] = stage = "published"
        _save(project_id, state)

    if stage == "published":
        await workspace_acl.configure_tree(name, path)
        await workspace_mount.attach(project_id, path)
        state["stage"] = stage = "mounted"
        _save(project_id, state)

    if stage == "mounted":
        current = await workspace_mount.device(name)
        if current != (str(path), workspace_mount.TARGET):
            raise container.VibeError("vibe_workspace_migration_failed")
        if state["was_running"] and not await container.running(project_id):
            await container.start(project_id)
        workspace_mount.clear_migration(project_id)
