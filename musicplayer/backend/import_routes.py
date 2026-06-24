"""Import generierter Musik aus den Workspaces (Admin-only).

Scannt data_dir/workspaces/**/generated/*.mp3 und kopiert ausgewählte Stücke in
den Player-Pool. Quelldateien bleiben unangetastet (kopieren, nicht verschieben).
Dedup über den relativen Quellpfad (Spalte `source`).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded

from . import storage, tracks_store

router = APIRouter(prefix="/generated")

AdminAuth = Annotated[tuple[str, str], Depends(require_admin)]


def _rel(path) -> str:
    return str(path.relative_to(storage.workspaces_root()))


def _workspace_label(rel_path: str) -> str:
    """z.B. 'projects/019eacac…' aus '<kind>/<id>/generated/<file>.mp3'."""
    parts = rel_path.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1][:8]}"
    return parts[0] if parts else rel_path


def _title_for(rel_path: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"Generiert · {_workspace_label(rel_path)} · {date}"


class ImportIn(BaseModel):
    path: str = Field(min_length=1, max_length=512)


@router.get("")
def list_generated(_: AdminAuth) -> list[dict]:
    imported = tracks_store.imported_sources()
    out: list[dict] = []
    for p in storage.scan_generated():
        rel = _rel(p)
        st = p.stat()
        out.append({
            "path": rel,
            "workspace": _workspace_label(rel),
            "size_bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "already_imported": rel in imported,
        })
    return out


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_generated(body: ImportIn, auth: AdminAuth) -> dict:
    admin, _ = auth
    rel = body.path.strip()
    if rel in tracks_store.imported_sources():
        raise coded(status.HTTP_409_CONFLICT, "already_imported")
    src = storage.resolve_in_workspaces(rel)
    if src is None:
        raise coded(status.HTTP_404_NOT_FOUND, "source_not_found")

    filename = storage.copy_into_pool(src)
    title = _title_for(rel)
    track_id = tracks_store.add(title, filename, src.stat().st_size, admin, source=rel)
    return {"id": track_id, "title": title}
