"""API zum Auflisten und Importieren fester Projekt-Medienquellen."""
from __future__ import annotations

import json
import sqlite3
from pathlib import PurePosixPath
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from pydantic import BaseModel, Field

from . import sources, storage, tracks_store
from .access import require_project_access
from .media_formats import MediaKind, extension

router = APIRouter(tags=["musicplayer"])


class SourceOut(BaseModel):
    source: str
    group: str
    path: str
    kind: MediaKind
    title: str
    meta: dict[str, Any]
    size_bytes: int
    mtime: str
    already_imported: bool


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


@router.get("/projects/{project_id}/sources", response_model=list[SourceOut])
def list_project_sources(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
    kind: Annotated[MediaKind | None, Query()] = None,
):
    require_project_access(project_id, principal, "write")
    return sources.list_sources(project_id, kind=kind)


@router.get("/projects/{project_id}/generated", response_model=list[GeneratedTrack])
def list_generated_alias(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
    kind: Annotated[MediaKind | None, Query()] = None,
):
    require_project_access(project_id, principal, "write")
    return [
        {
            "path": item["path"],
            "workspace": str(PurePosixPath(item["path"]).parent),
            "size_bytes": item["size_bytes"],
            "mtime": item["mtime"],
            "already_imported": item["already_imported"],
        }
        for item in sources.list_sources(project_id, kind=kind, source="generated")
    ]


def _meta_json(meta: dict[str, Any]) -> str:
    return json.dumps(meta, ensure_ascii=False, separators=(",", ":")) if meta else ""


@router.post(
    "/projects/{project_id}/sources/import",
    response_model=ImportedTrack,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/generated/import",
    response_model=ImportedTrack,
    status_code=status.HTTP_201_CREATED,
)
def import_source(
    project_id: str,
    request: ImportRequest,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
):
    require_project_access(project_id, principal, "write")
    entry = sources.source_entry(project_id, request.path)
    if entry is None:
        raise HTTPException(status_code=404, detail="Medienquelle nicht gefunden")

    source_key = sources.source_key(project_id, request.path)
    if tracks_store.source_exists(project_id, source_key):
        raise HTTPException(status_code=409, detail="Track bereits importiert")

    safe = sources.safe_source_file(project_id, request.path)
    if safe is None:
        raise HTTPException(status_code=404, detail="Medienquelle nicht gefunden")
    source_path, _ = safe
    ext = extension(source_path.name)
    filename = storage.copy_into_library(project_id, source_path, ext=ext)
    copied = storage.file_path(project_id, filename)
    if copied is None:
        raise HTTPException(status_code=500, detail="Importierte Mediendatei nicht lesbar")
    title = entry["title"]
    if entry["source"] == "generated":
        title = f"Generiert · {source_path.stem}"
    try:
        track = tracks_store.add(
            project_id,
            title=title[:200],
            filename=filename,
            size_bytes=copied.stat().st_size,
            uploaded_by=principal.username,
            source=source_key,
            media_kind=entry["kind"],
            ext=ext,
            meta=_meta_json(entry["meta"]),
        )
    except sqlite3.IntegrityError as exc:
        storage.delete_file(project_id, filename)
        raise HTTPException(status_code=409, detail="Track bereits importiert") from exc
    except Exception:
        storage.delete_file(project_id, filename)
        raise
    return ImportedTrack(id=track["id"], title=track["title"])
