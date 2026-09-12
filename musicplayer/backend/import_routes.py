"""Projektlokaler Import generierter MP3-Dateien in die Musicplayer-Bibliothek."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

from . import storage, tracks_store
from .access import require_project_access

router = APIRouter(tags=["musicplayer"])


class GeneratedTrack(BaseModel):
    path: str
    workspace: str
    size_bytes: int
    mtime: str
    already_imported: bool


class ImportRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class ImportedTrack(BaseModel):
    id: int
    title: str


def _source_key(project_id: str, relative: str) -> str:
    return f"projects/{project_id}/{relative}"


def _safe_generated_file(project_id: str, relative: str) -> Path | None:
    if "\\" in relative:
        return None
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        return None
    if "generated" not in pure.parts or not relative.lower().endswith(".mp3"):
        return None

    root = storage.project_workspace(project_id)
    candidate = root.joinpath(*pure.parts)
    if candidate.is_symlink() or not candidate.is_file():
        return None
    try:
        if not candidate.resolve().is_relative_to(root.resolve()):
            return None
    except OSError:
        return None
    return candidate


def _scan_generated(project_id: str) -> list[dict]:
    root = storage.project_workspace(project_id)
    imported = tracks_store.imported_sources(project_id)
    found: list[dict] = []
    if not root.is_dir():
        return found

    for candidate in root.rglob("*.mp3"):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        try:
            resolved = candidate.resolve()
            if not resolved.is_relative_to(root.resolve()):
                continue
            relative = candidate.relative_to(root).as_posix()
            stat = candidate.stat()
        except (OSError, ValueError):
            continue
        if "generated" not in PurePosixPath(relative).parts:
            continue
        found.append({
            "path": relative,
            "workspace": str(PurePosixPath(relative).parent),
            "size_bytes": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "already_imported": _source_key(project_id, relative) in imported,
            "_mtime": stat.st_mtime,
        })
    found.sort(key=lambda item: item["_mtime"], reverse=True)
    for item in found:
        item.pop("_mtime", None)
    return found


@router.get("/projects/{project_id}/generated", response_model=list[GeneratedTrack])
def list_generated(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
):
    require_project_access(project_id, principal, "write")
    return _scan_generated(project_id)


@router.post(
    "/projects/{project_id}/generated/import",
    response_model=ImportedTrack,
    status_code=status.HTTP_201_CREATED,
)
def import_generated(
    project_id: str,
    request: ImportRequest,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
):
    require_project_access(project_id, principal, "write")
    source = _safe_generated_file(project_id, request.path)
    if source is None:
        raise HTTPException(status_code=404, detail="Generierte MP3 nicht gefunden")

    source_key = _source_key(project_id, request.path)
    if tracks_store.source_exists(project_id, source_key):
        raise HTTPException(status_code=409, detail="Track bereits importiert")

    filename = storage.copy_into_library(project_id, source)
    copied = storage.file_path(project_id, filename)
    if copied is None:
        raise HTTPException(status_code=500, detail="Importierte Audiodatei nicht lesbar")
    try:
        track = tracks_store.add(
            project_id,
            title=f"Generiert · {source.stem}"[:200],
            filename=filename,
            size_bytes=copied.stat().st_size,
            uploaded_by=principal.username,
            source=source_key,
        )
    except sqlite3.IntegrityError as exc:
        storage.delete_file(project_id, filename)
        raise HTTPException(status_code=409, detail="Track bereits importiert") from exc
    except Exception:
        storage.delete_file(project_id, filename)
        raise
    return ImportedTrack(id=track["id"], title=track["title"])
