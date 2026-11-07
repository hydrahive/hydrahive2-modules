"""Core-project provisioning and Samba projection for Game Studio."""

from __future__ import annotations

import logging

from hydrahive.llm.client import default_model
from hydrahive.projects import config as project_config
from hydrahive.samba import disable_share, enable_share, is_share_enabled
from hydrahive.samba import manager as samba_manager
from hydrahive.samba.manager import share_name_for

from . import workspace_files
from .models import ProjectCreate, WorkspaceProject

logger = logging.getLogger(__name__)


class ProjectProvisionError(RuntimeError):
    pass


def _is_game_project(config: dict) -> bool:
    metadata = config.get("metadata")
    return isinstance(metadata, dict) and isinstance(metadata.get("game_studio"), dict)


def _share_label(project_id: str) -> str:
    return f"game_{project_id[:8]}"


def _sharing(config: dict) -> dict:
    enabled = bool(config.get("samba_enabled")) and is_share_enabled(config["id"])
    return {
        "enabled": enabled,
        "share_name": share_name_for(config["id"], _share_label(config["id"])),
        "user": samba_manager.share_user(),
        "platform": "mac" if samba_manager.is_mac() else "linux",
    }


def public_project(config: dict, project: WorkspaceProject) -> dict:
    return {**project.model_dump(mode="json"), "sharing": _sharing(config)}


def list_for(username: str, role: str) -> list[dict]:
    configs = project_config.list_all() if role == "admin" else project_config.list_for_user(username)
    result: list[dict] = []
    for config in configs:
        if not _is_game_project(config):
            continue
        project = workspace_files.read(config["id"])
        if project is not None:
            result.append(public_project(config, project))
    result.sort(key=lambda item: (item["updated_at"], item["project_id"]), reverse=True)
    return result


def get(project_id: str) -> tuple[dict, WorkspaceProject] | None:
    config = project_config.get(project_id)
    if config is None or not _is_game_project(config):
        return None
    project = workspace_files.read(project_id)
    return (config, project) if project is not None else None


def create(username: str, body: ProjectCreate) -> dict:
    model = default_model().strip()
    if not model:
        raise ProjectProvisionError("game_studio_llm_not_configured")
    config: dict | None = None
    try:
        config = project_config.create(
            name=body.title,
            description="Game-Studio-Projekt mit kanonischen Workspace-Dateien",
            members=[],
            llm_model=model,
            created_by=username,
            init_git=True,
            metadata={"game_studio": {"schema_version": 1}},
        )
        project = workspace_files.create(config["id"], body)
        enabled, error = enable_share(config["id"], _share_label(config["id"]))
        if not enabled:
            raise ProjectProvisionError(error or "samba_failed")
        config = project_config.update(config["id"], samba_enabled=True)
        return public_project(config, project)
    except Exception:
        if config is not None:
            try:
                disable_share(config["id"])
                project_config.delete(config["id"])
            except Exception:
                logger.exception("Game-Studio-Projekt %s konnte nicht kompensiert werden", config["id"])
        raise


def update(config: dict, revision: int, changes: dict[str, object]) -> dict:
    project = workspace_files.update(config["id"], revision, changes)
    if project.title != config["name"]:
        config = project_config.update(config["id"], name=project.title)
    return public_project(config, project)


def generate_unreal(config: dict, revision: int) -> dict:
    project = workspace_files.generate_unreal(config["id"], revision)
    return public_project(config, project)
