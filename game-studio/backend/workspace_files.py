"""Canonical Game Studio project files inside Core project workspaces."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from hydrahive.db._utils import now_iso
from hydrahive.projects._paths import ensure_workspace

from .models import ProjectCreate, WorkspaceProject

_DATA_DIR = "game-studio"
_PROJECT_FILE = "project.json"


class WorkspaceFileError(RuntimeError):
    pass


def _directory(project_id: str) -> Path:
    root = ensure_workspace(project_id)
    directory = root / _DATA_DIR
    if directory.is_symlink():
        raise WorkspaceFileError("game_studio_workspace_symlink")
    directory.mkdir(mode=0o2775, parents=True, exist_ok=True)
    if not directory.resolve().is_relative_to(root):
        raise WorkspaceFileError("game_studio_workspace_escape")
    return directory


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o664)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _brief(project: WorkspaceProject) -> str:
    return (
        f"# {project.title}\n\n"
        f"## Idee\n\n{project.idea or 'Noch nicht beschrieben.'}\n\n"
        f"## Genre\n\n{project.genre or 'Noch nicht festgelegt.'}\n\n"
        f"## Engine\n\n{project.engine}\n\n"
        f"## Zielplattform\n\n{project.target_platform}\n"
    )


def _vertical_slice(project: WorkspaceProject) -> str:
    return (
        "# Kleinster spielbarer Kern\n\n"
        f"## Kernaktion\n\n{project.core_action or 'Noch nicht festgelegt.'}\n\n"
        f"## Sichtbares Erfolgskriterium\n\n{project.success_condition or 'Noch nicht festgelegt.'}\n"
    )


def _readme(project: WorkspaceProject) -> str:
    return (
        "# Game Studio\n\n"
        "Dieser Ordner enthält die kanonischen Planungsdaten des Projekts. "
        "Das Engine-Projekt liegt im übergeordneten Workspace und wird über dessen Samba-Freigabe geöffnet.\n\n"
        f"- Engine: `{project.engine}`\n"
        "- `project.json`: maschinenlesbarer Projektstand\n"
        "- `game-brief.md`: Idee, Genre und Zielplattform\n"
        "- `vertical-slice.md`: kleinster spielbarer Kern und Erfolgskriterium\n"
    )


def write(project: WorkspaceProject) -> None:
    directory = _directory(project.project_id)
    # project.json is the commit marker and is replaced last.
    _atomic_write(directory / "game-brief.md", _brief(project))
    _atomic_write(directory / "vertical-slice.md", _vertical_slice(project))
    _atomic_write(directory / "README.md", _readme(project))
    encoded = json.dumps(project.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_write(directory / _PROJECT_FILE, encoded)


def create(project_id: str, body: ProjectCreate) -> WorkspaceProject:
    timestamp = now_iso()
    project = WorkspaceProject(
        project_id=project_id,
        entry_kind=body.entry_kind,
        engine=body.engine,
        title=body.title,
        idea=body.idea.strip(),
        genre=body.genre.strip(),
        target_platform=body.target_platform,
        created_at=timestamp,
        updated_at=timestamp,
    )
    write(project)
    return project


def read(project_id: str) -> WorkspaceProject | None:
    path = _directory(project_id) / _PROJECT_FILE
    try:
        return WorkspaceProject.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise WorkspaceFileError("game_studio_project_file_invalid") from exc


def update(project_id: str, revision: int, changes: dict[str, object]) -> WorkspaceProject:
    current = read(project_id)
    if current is None:
        raise WorkspaceFileError("game_studio_project_file_missing")
    if current.revision != revision:
        raise WorkspaceFileError("game_studio_revision_conflict")
    values = current.model_dump(mode="python")
    values.update({key: value for key, value in changes.items() if value is not None})
    values.update(revision=revision + 1, updated_at=now_iso())
    updated = WorkspaceProject.model_validate(values)
    write(updated)
    return updated
