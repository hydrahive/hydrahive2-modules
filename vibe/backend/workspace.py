"""Öffentliche Orchestrierung des gemeinsamen Host-/Container-Workspaces.

Jeder Vorgang (Mount, Migration, Löschen) läuft unter einer Projektsperre (`workspace_lock.project`); Migration und
Container-Stopp zusätzlich bei ruhiggestellten Agentenläufen (`workspace_lock.quiesced`).
"""

from __future__ import annotations

from pathlib import Path

from . import container, incus, workspace_lock, workspace_migration, workspace_mount

# Stabiler Vertrag für Tests und angrenzende Vibe-Dienste.
DEVICE = workspace_mount.DEVICE
TARGET = workspace_mount.TARGET
_marker = workspace_mount.marker


def _require_project(project_id: str) -> None:
    """Unter der Sperre: das Kern-Projekt muss noch existieren. Ein Nachzügler (z. B. ein Chat-Aufruf, der erst nach dem
    Löschen die Sperre bekommt) darf weder den Host-Workspace neu anlegen noch eine Sperrdatei zurücklassen."""
    from hydrahive.projects import config as project_config

    if project_config.get(project_id) is None:
        workspace_lock.discard(project_id)
        raise container.VibeError("vibe_project_not_found")


async def attach_new(project_id: str) -> None:
    """Leeren Host-Workspace eines neuen Projekts vor der Einrichtung mounten."""
    async with workspace_lock.project(project_id):
        _require_project(project_id)
        path = workspace_mount.host_path(project_id)
        if any(path.iterdir()):
            raise container.VibeError("vibe_workspace_conflict")
        await workspace_mount.attach(project_id, path)


def forget(project_id: str) -> None:
    """Migrationszustand eines endgültig entfernten Projekts löschen (die Sperrdatei entfernt `projects.remove`
    selbst, und zwar unter der Sperre – hier nie: sie könnte gerade gehalten werden)."""
    container.name_for(project_id)
    workspace_mount.clear_migration(project_id)


async def _strip_in_container(project_id: str) -> None:
    """`o+w` entfernen, wo der Containernutzer Besitzer ist: der Hostdienst darf Dateien der abgebildeten UID nicht per
    `chmod` ändern (echte Probe 6.11.). Läuft nur in einem bereits laufenden Container; Symlinks bleiben unberührt."""
    if not await container.running(project_id):
        return
    rc, _, _ = await incus.run(
        "exec", container.name_for(project_id), "--user", "1000", "--",
        "find", workspace_mount.TARGET, "!", "-type", "l", "-perm", "-o+w", "-exec", "chmod", "o-w", "{}", "+",
        timeout=120,
    )
    if rc != 0:
        raise container.VibeError("vibe_workspace_unavailable")


async def _ready(project_id: str, path: Path) -> str:
    # Wurzel-ACL vollständig neu setzen und `o+w` im ganzen Baum entfernen (der Containernutzer kann `chmod 777`).
    await workspace_mount.attach(project_id, path)
    await _strip_in_container(project_id)
    return "ready"


async def ensure(project_id: str, *, agent_id: str = "") -> str:
    """Mount sicherstellen; bestehende interne `/work`-Daten crash-fest migrieren."""
    name = container.name_for(project_id)
    async with workspace_lock.project(project_id):
        _require_project(project_id)
        path = workspace_mount.host_path(project_id)
        pending = workspace_mount.marker(project_id).exists()
        current = await workspace_mount.device(name)
        if current is not None and not pending:
            if current != (str(path), TARGET):
                raise container.VibeError("vibe_workspace_conflict")
            return await _ready(project_id, path)

        async with workspace_lock.quiesced(agent_id, project_id) as quiet:
            was_running = await container.running(project_id)
            await workspace_migration.migrate(
                project_id, path, was_running=was_running, before_stop=quiet.refresh
            )
        return "migrated" if pending or any(path.iterdir()) else "attached"
