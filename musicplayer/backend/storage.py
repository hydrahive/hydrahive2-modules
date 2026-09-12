"""Sicherer, projektgebundener Dateispeicher für MP3-Tracks."""
from __future__ import annotations

import filecmp
import os
import re
import shutil
import uuid
from pathlib import Path

from hydrahive.projects import workspace_path
from hydrahive.settings import settings

ALLOWED_MIME = {"audio/mpeg", "audio/mp3", "audio/x-mpeg", "application/octet-stream"}
_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,127}$")


def _validate_project_id(project_id: str) -> str:
    if not _PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("invalid_project_id")
    return project_id


def project_workspace(project_id: str) -> Path:
    """Liefert einen Workspace-Pfad, der nicht per Symlink ausbrechen kann."""
    root = workspace_path(_validate_project_id(project_id))
    projects_root = settings.data_dir / "workspaces" / "projects"
    if root.is_symlink() or not root.resolve().is_relative_to(projects_root.resolve()):
        raise ValueError("project_workspace_symlink")
    return root


def audio_dir(project_id: str) -> Path:
    """Erzeugt `<project>/media/audio` ohne Symlink-Ausbruch aus dem Workspace."""
    root = project_workspace(project_id)
    root.mkdir(parents=True, exist_ok=True)
    projects_root = settings.data_dir / "workspaces" / "projects"
    if root.is_symlink() or not root.resolve().is_relative_to(projects_root.resolve()):
        raise ValueError("project_workspace_symlink")

    media = root / "media"
    if media.is_symlink():
        raise ValueError("media_directory_symlink")
    media.mkdir(exist_ok=True)

    directory = media / "audio"
    if directory.is_symlink():
        raise ValueError("audio_directory_symlink")
    directory.mkdir(exist_ok=True)
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("audio_directory_outside_project")

    for parent in (media, directory):
        try:
            os.chmod(parent, 0o2775)
        except OSError:
            pass
    return directory


def legacy_storage_dir() -> Path:
    """Alter globaler Ablageort aus Musicplayer-Versionen vor Projekt-Scope."""
    return settings.data_dir / "modules" / "musicplayer"


def is_allowed_upload(filename: str, content_type: str | None) -> bool:
    """Prüft Dateiendung und — falls vorhanden — den gemeldeten MIME-Type."""
    if not filename.lower().endswith(".mp3"):
        return False
    return content_type is None or content_type.lower() in ALLOWED_MIME


def _valid_filename(filename: str) -> bool:
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        return False
    if not filename.lower().endswith(".mp3"):
        return False
    try:
        uuid.UUID(filename[:-4])
    except (ValueError, AttributeError):
        return False
    return True


def save_bytes(project_id: str, data: bytes) -> str:
    """Speichert Bytes atomar unter servergeneriertem UUID-Dateinamen."""
    filename = f"{uuid.uuid4()}.mp3"
    destination = audio_dir(project_id) / filename
    temporary = destination.with_suffix(".mp3.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return filename


def copy_into_library(project_id: str, source: Path) -> str:
    """Kopiert eine reguläre Quelldatei atomar und prüft die Kopie byteweise."""
    if source.is_symlink() or not source.is_file():
        raise ValueError("invalid_source")
    filename = f"{uuid.uuid4()}.mp3"
    destination = audio_dir(project_id) / filename
    temporary = destination.with_suffix(".mp3.tmp")
    try:
        shutil.copy2(source, temporary, follow_symlinks=False)
        if temporary.is_symlink() or not temporary.is_file():
            raise OSError("audio_copy_not_regular")
        if not filecmp.cmp(source, temporary, shallow=False):
            raise OSError("audio_copy_verification_failed")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return filename


def _legacy_path(filename: str) -> Path | None:
    if not _valid_filename(filename):
        return None
    root = legacy_storage_dir()
    candidate = root / filename
    if candidate.is_symlink() or not candidate.is_file():
        return None
    try:
        if not candidate.resolve().is_relative_to(root.resolve()):
            return None
    except OSError:
        return None
    return candidate


def _migrate_legacy_file(project_id: str, filename: str, expected_size: int | None) -> Path | None:
    """Kopiert eine Legacy-Datei, verifiziert sie und entfernt erst dann die Quelle."""
    source = _legacy_path(filename)
    if source is None:
        return None
    source_size = source.stat().st_size
    if expected_size is not None and source_size != expected_size:
        return None

    destination = audio_dir(project_id) / filename
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            return None
        if not filecmp.cmp(source, destination, shallow=False):
            return None
        source.unlink()
        return destination

    temporary = destination.with_suffix(f".mp3.migrate-{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(source, temporary, follow_symlinks=False)
        if temporary.is_symlink() or not temporary.is_file():
            return None
        if temporary.stat().st_size != source_size or not filecmp.cmp(source, temporary, shallow=False):
            return None
        os.replace(temporary, destination)
        if destination.stat().st_size != source_size:
            destination.unlink(missing_ok=True)
            return None
        source.unlink()
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def file_path(project_id: str, filename: str, expected_size: int | None = None) -> Path | None:
    """Löst ausschließlich sichere UUID-Dateinamen innerhalb eines Projekts auf.

    Falls der Track noch im Legacy-Pool liegt, wird er beim ersten Zugriff sicher in
    den Projektworkspace übernommen.
    """
    if not _valid_filename(filename):
        return None
    root = audio_dir(project_id)
    candidate = root / filename
    if candidate.is_symlink():
        return None
    try:
        if candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()):
            if expected_size is None or candidate.stat().st_size == expected_size:
                return candidate
            return None
    except OSError:
        return None
    return _migrate_legacy_file(project_id, filename, expected_size)


def delete_file(project_id: str, filename: str) -> None:
    path = file_path(project_id, filename)
    if path is not None:
        path.unlink(missing_ok=True)
