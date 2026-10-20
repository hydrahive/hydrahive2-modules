"""Sammlung (Spec §12.1): Liste je Kette, Einzelansicht, Herunterladen, Papierkorb, endgültig löschen."""
from __future__ import annotations

import re
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import FileResponse
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import chains, preview, store
from .device_routes import HEADERS

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
_UNSAFE = re.compile(r"[^\w.-]+", re.UNICODE)


def file_name(title: str) -> str:
    base = _UNSAFE.sub("-", title or "").strip("-.")
    return f"{base[:80] or 'diagramm'}.html"


def _project_names() -> dict[str, str]:
    from hydrahive.projects._config_io import list_all
    return {p["id"]: p.get("name") or p["id"] for p in list_all() if p.get("id")}


def _visible(view_id: str, auth: tuple[str, str]) -> dict[str, Any]:
    row = store.get(view_id)
    if not store.can_view(row, *auth):
        raise coded(404, "diagram_not_found")
    return row  # type: ignore[return-value]


def _changeable(view_id: str, auth: tuple[str, str]) -> dict[str, Any]:
    row = _visible(view_id, auth)
    if not chains.can_change(row, *auth):
        raise coded(403, "diagram_not_owner")
    return row


@router.get("/list")
def list_diagrams(auth: Auth, project: str | None = Query(None, max_length=80), q: str = Query("", max_length=200),
                  trash: int = Query(0, ge=0, le=1)) -> list[dict[str, Any]]:
    rows = chains.newest_per_chain(store.list_for(*auth, trash=bool(trash)))
    if project == "none":
        rows = [r for r in rows if not r["project_id"]]
    elif project:
        rows = [r for r in rows if r["project_id"] == project]
    if q.strip():
        needle = q.strip().casefold()
        rows = [r for r in rows if needle in r["title"].casefold()]
    names = _project_names()
    return [dict(r, project_name=names.get(r["project_id"] or "", "")) for r in rows]


@router.get("/item/{view_id}")
def item(view_id: str, auth: Auth) -> dict[str, Any]:
    row = _visible(view_id, auth)
    versions = [{"id": v["id"], "created_at": v["created_at"], "deleted_at": v["deleted_at"]}
                for v in store.versions(view_id)]
    return dict(row, versions=versions)


@router.get("/download/{view_id}")
def download(view_id: str, auth: Auth) -> Response:
    row = _visible(view_id, auth)
    page = store.html(view_id) or ""
    name = file_name(row["title"])
    headers = dict(HEADERS, **{"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})
    return Response(page, media_type="text/html; charset=utf-8", headers=headers)


@router.get("/preview/{view_id}")
def preview_image(view_id: str, auth: Auth) -> FileResponse:
    _visible(view_id, auth)
    path = preview.path_if_ready(view_id)
    if path is None:
        raise coded(404, "diagram_not_found")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.post("/trash/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def trash(view_id: str, auth: Auth) -> None:
    _changeable(view_id, auth)
    chains.trash_chain(view_id)


@router.post("/restore/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def restore(view_id: str, auth: Auth) -> None:
    _changeable(view_id, auth)
    chains.restore_chain(view_id)


@router.delete("/item/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def purge(view_id: str, auth: Auth) -> None:
    row = _changeable(view_id, auth)
    if not row["deleted_at"]:
        raise coded(409, "diagram_not_in_trash")
    chains.purge_chain(view_id)
