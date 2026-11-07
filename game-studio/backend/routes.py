"""Authenticated API for workspace-backed Game Studio projects."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access

from . import overview, projects, unreal_project, workspace_files
from .models import ProjectCreate, ProjectGenerate, ProjectUpdate, WorkspaceProject

router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]


def _game_project(project_id: str, principal: AuthPrincipal, required: str) -> tuple[dict, WorkspaceProject]:
    found = projects.get(project_id)
    if found is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_studio_project_not_found")
    config, project = found
    check_project_access(config, principal.username, principal.role, required=required)
    return config, project


def _step_is_complete(current: WorkspaceProject, changes: dict[str, object]) -> bool:
    merged = {**current.model_dump(mode="python"), **changes}
    step = int(merged.get("current_step", 1))
    if step >= 2 and not (str(merged.get("title", "")).strip() and str(merged.get("idea", "")).strip()):
        return False
    if step >= 3 and not str(merged.get("genre", "")).strip():
        return False
    if step < 4:
        return True
    return bool(
        str(merged.get("core_action", "")).strip() and str(merged.get("success_condition", "")).strip()
    )


def _provision_error(exc: projects.ProjectProvisionError) -> None:
    code = str(exc)
    http_status = status.HTTP_400_BAD_REQUEST if code == "samba_not_installed" else status.HTTP_409_CONFLICT
    raise coded(http_status, code)


@router.get("/overview")
def get_overview(principal: Principal) -> dict:
    return overview.overview(principal.username, principal.role)


@router.get("/projects/{project_id}")
def get_project(project_id: str, principal: Principal) -> dict:
    config, project = _game_project(project_id, principal, "read")
    return projects.public_project(config, project)


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, principal: Principal) -> dict:
    if principal.role != "admin":
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
    try:
        return projects.create(principal.username, body)
    except projects.ProjectProvisionError as exc:
        _provision_error(exc)
    except workspace_files.WorkspaceFileError as exc:
        raise coded(status.HTTP_409_CONFLICT, str(exc))


@router.post("/projects/{project_id}/unreal-project")
def generate_unreal_project(project_id: str, body: ProjectGenerate, principal: Principal) -> dict:
    config, _current = _game_project(project_id, principal, "write")
    try:
        return projects.generate_unreal(config, body.revision)
    except unreal_project.UnrealProjectError as exc:
        code = str(exc)
        http_status = status.HTTP_400_BAD_REQUEST if code in {
            "game_studio_unreal_engine_required", "game_studio_step_incomplete",
        } else status.HTTP_409_CONFLICT
        raise coded(http_status, code)
    except workspace_files.WorkspaceFileError as exc:
        code = str(exc)
        http_status = status.HTTP_409_CONFLICT if code.endswith("conflict") else status.HTTP_400_BAD_REQUEST
        raise coded(http_status, code)


@router.patch("/projects/{project_id}")
def update_project(project_id: str, body: ProjectUpdate, principal: Principal) -> dict:
    config, current = _game_project(project_id, principal, "write")
    changes = body.model_dump(exclude={"revision"}, exclude_unset=True)
    for field in ("title", "idea", "genre", "core_action", "success_condition"):
        if field in changes and isinstance(changes[field], str):
            changes[field] = changes[field].strip()
    if not _step_is_complete(current, changes):
        raise coded(status.HTTP_400_BAD_REQUEST, "game_studio_step_incomplete")
    try:
        return projects.update(config, body.revision, changes)
    except projects.ProjectProvisionError as exc:
        _provision_error(exc)
    except workspace_files.WorkspaceFileError as exc:
        code = str(exc)
        http_status = status.HTTP_409_CONFLICT if code.endswith("conflict") else status.HTTP_400_BAD_REQUEST
        raise coded(http_status, code)
