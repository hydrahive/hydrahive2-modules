"""Sicherer, projektgebundener Dateispeicher für Audio und Video."""
from __future__ import annotations

import filecmp
import os
import re
import shutil
import uuid
from pathlib import Path

from hydrahive.projects import workspace_path
from hydrahive.settings import settings

from .media_formats import MEDIA_FORMATS, MediaKind, extension, format_for

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


def _library_dir(project_id: str, kind: MediaKind) -> Path:
    root = project_workspace(project_id)
    root.mkdir(parents=True, exist_ok=True)
    media = root / "media"
    if media.is_symlink():
        raise ValueError("media_directory_symlink")
    media.mkdir(exist_ok=True)
    directory = media / kind
    if directory.is_symlink():
        raise ValueError(f"{kind}_directory_symlink")
    directory.mkdir(exist_ok=True)
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"{kind}_directory_outside_project")
    for parent in (media, directory):
        try:
            os.chmod(parent, 0o2775)
        except OSError:
            pass
    return directory


def audio_dir(project_id: str) -> Path:
    return _library_dir(project_id, "audio")


def video_dir(project_id: str) -> Path:
    return _library_dir(project_id, "video")


def legacy_storage_dir() -> Path:
    return settings.data_dir / "modules" / "musicplayer"


def media_kind(filename: str | Path) -> MediaKind | None:
    media_format = format_for(filename)
    return media_format.kind if media_format else None


def is_allowed_upload(filename: str, content_type: str | None = None) -> bool:
    """Validiert ausschließlich die Endung; Client-MIME ist nicht vertrauenswürdig."""
    del content_type
    return format_for(filename) is not None


def _valid_filename(filename: str) -> bool:
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        return False
    ext = extension(filename)
    if not ext:
        return False
    try:
        uuid.UUID(Path(filename).stem)
    except (ValueError, AttributeError):
        return False
    return True


def _destination(project_id: str, ext: str) -> tuple[str, Path]:
    media_format = MEDIA_FORMATS.get(ext.lower())
    if media_format is None:
        raise ValueError("unsupported_media_extension")
    filename = f"{uuid.uuid4()}.{ext.lower()}"
    directory = audio_dir(project_id) if media_format.kind == "audio" else video_dir(project_id)
    return filename, directory / filename


def save_bytes(project_id: str, data: bytes, ext: str = "mp3") -> str:
    """Speichert Bytes atomar unter servergeneriertem UUID-Dateinamen."""
    filename, destination = _destination(project_id, ext)
    temporary = destination.with_name(f"{destination.name}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return filename


def copy_into_library(project_id: str, source: Path, ext: str | None = None) -> str:
    """Kopiert eine reguläre Workspace-Quelldatei atomar und verifiziert sie."""
    root = project_workspace(project_id)
    if source.is_symlink() or not source.is_file():
        raise ValueError("invalid_source")
    try:
        if not source.resolve().is_relative_to(root.resolve()):
            raise ValueError("source_outside_project")
    except OSError as exc:
        raise ValueError("invalid_source") from exc
    source_ext = extension(source)
    if not source_ext or (ext is not None and source_ext != ext.lower()):
        raise ValueError("unsupported_media_extension")
    filename, destination = _destination(project_id, source_ext)
    temporary = destination.with_name(f"{destination.name}.tmp")
    try:
        shutil.copy2(source, temporary, follow_symlinks=False)
        if temporary.is_symlink() or not temporary.is_file():
            raise OSError("media_copy_not_regular")
        if not filecmp.cmp(source, temporary, shallow=False):
            raise OSError("media_copy_verification_failed")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return filename


def _legacy_path(filename: str) -> Path | None:
    if not _valid_filename(filename) or extension(filename) != "mp3":
        return None
    root = legacy_storage_dir()
    candidate = root / filename
    if candidate.is_symlink() or not candidate.is_file():
        return None
    try:
        return candidate if candidate.resolve().is_relative_to(root.resolve()) else None
    except OSError:
        return None


def _migrate_legacy_file(project_id: str, filename: str, expected_size: int | None) -> Path | None:
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
    temporary = destination.with_name(f"{destination.name}.migrate-{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(source, temporary, follow_symlinks=False)
        if temporary.is_symlink() or temporary.stat().st_size != source_size:
            return None
        if not filecmp.cmp(source, temporary, shallow=False):
            return None
        os.replace(temporary, destination)
        source.unlink()
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def file_path(project_id: str, filename: str, expected_size: int | None = None) -> Path | None:
    """Löst sichere UUID-Dateien auf und übernimmt bestehende MP3s weiterhin lazy."""
    if not _valid_filename(filename):
        return None
    media_format = format_for(filename)
    if media_format is None:
        return None
    root = audio_dir(project_id) if media_format.kind == "audio" else video_dir(project_id)
    candidate = root / filename
    if candidate.is_symlink():
        return None
    try:
        if candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()):
            return candidate if expected_size is None or candidate.stat().st_size == expected_size else None
    except OSError:
        return None
    return _migrate_legacy_file(project_id, filename, expected_size)


def delete_file(project_id: str, filename: str) -> None:
    path = file_path(project_id, filename)
    if path is not None:
        path.unlink(missing_ok=True)
