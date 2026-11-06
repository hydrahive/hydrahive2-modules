"""Hostpfad, Incus-Disk-Device und ACL des gemeinsamen Vibe-Workspaces."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import container, incus, workspace_acl

DEVICE = "workspace"
TARGET = "/work"


def host_path(project_id: str) -> Path:
    container.name_for(project_id)  # validiert die ID vor jeder Pfadbildung
    from hydrahive.projects._paths import ensure_workspace, workspace_path

    lexical = workspace_path(project_id)
    root = lexical.parent.resolve()
    path = ensure_workspace(project_id).resolve()
    # Ein nachträglich gesetzter Workspace-Symlink darf nie einen beliebigen
    # Hostpfad in den Container hineinreichen.
    if path != root / project_id:
        raise container.VibeError("vibe_workspace_unavailable")
    return path


def _migration_path(project_id: str) -> Path:
    from hydrahive.settings import settings

    container.name_for(project_id)
    return settings.data_dir / "vibe" / "workspace-migrations" / project_id


def migration_root(project_id: str) -> Path:
    root = _migration_path(project_id)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def marker(project_id: str) -> Path:
    return migration_root(project_id) / "state.json"


def staging(project_id: str) -> Path:
    return migration_root(project_id) / "pull"


def clear_migration(project_id: str) -> None:
    root = _migration_path(project_id)
    if root.exists():
        shutil.rmtree(root)


async def device(name: str) -> tuple[str, str] | None:
    rc, source, err = await incus.run("config", "device", "get", name, DEVICE, "source")
    if rc != 0:
        message = err.lower()
        missing = (
            "not found" in message
            or "doesn't exist" in message
            or "does not exist" in message
        )
        if missing:
            return None
        raise container.VibeError("vibe_workspace_unavailable")
    rc, target, _ = await incus.run("config", "device", "get", name, DEVICE, "path")
    if rc != 0:
        raise container.VibeError("vibe_workspace_conflict")
    return source.strip(), target.strip()


async def attach(project_id: str, path: Path) -> None:
    name = container.name_for(project_id)
    current = await device(name)
    if current is not None:
        if current != (str(path), TARGET):
            raise container.VibeError("vibe_workspace_conflict")
        await workspace_acl.configure(name, path)
        return
    await workspace_acl.configure(name, path)
    rc, _, _ = await incus.run(
        "config",
        "device",
        "add",
        name,
        DEVICE,
        "disk",
        f"source={path}",
        f"path={TARGET}",
    )
    if rc != 0:
        raise container.VibeError("vibe_workspace_unavailable")


async def remove(name: str) -> bool:
    rc, _, _ = await incus.run("config", "device", "remove", name, DEVICE)
    return rc == 0
