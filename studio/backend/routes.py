"""Studio – REST unter /api/modules/studio (studio/SPEC.md).

Alle Projekt-Routen prüfen Mitgliedschaft (fremdes oder unbekanntes Projekt → 404). Dateien liefert der Kern über
/api/files aus (mit Range und Rechteprüfung) – das Modul hat keinen eigenen Datei-Endpunkt.
"""
from __future__ import annotations

import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.projects._config_io import list_for_user

from . import library

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
_PROJECT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _guard(user: str, project_id: str) -> None:
    if not _PROJECT_ID.match(project_id or "") or not any(p.get("id") == project_id for p in list_for_user(user)):
        raise coded(404, "studio_project_not_found")


@router.get("/projects")
def list_projects(auth: Auth) -> dict:
    return {"projects": [{"id": p["id"], "name": p.get("name") or p["id"]} for p in list_for_user(auth[0])]}


@router.get("/projects/{project_id}/library")
async def get_library(project_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return await asyncio.to_thread(library.list_items, project_id)
