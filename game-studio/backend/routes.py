"""Authenticated API for the visible Game Studio concept flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import overview, store
from .models import DraftCreate, DraftUpdate

router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]


def _step_is_complete(current: dict, changes: dict[str, object]) -> bool:
    merged = {**current, **changes}
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


@router.get("/overview")
def get_overview(principal: Principal) -> dict:
    return overview.overview(principal.user_id)


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str, principal: Principal) -> dict:
    draft = store.get(principal.user_id, draft_id)
    if draft is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_studio_draft_not_found")
    return draft


@router.post("/drafts", status_code=status.HTTP_201_CREATED)
def create_draft(body: DraftCreate, principal: Principal) -> dict:
    try:
        return store.create(
            principal.user_id,
            entry_kind=body.entry_kind,
            title=body.title.strip(),
            idea=body.idea.strip(),
            genre=body.genre.strip(),
            target_platform=body.target_platform,
        )
    except store.DraftConflict as exc:
        raise coded(status.HTTP_409_CONFLICT, str(exc))


@router.patch("/drafts/{draft_id}")
def update_draft(draft_id: str, body: DraftUpdate, principal: Principal) -> dict:
    changes = body.model_dump(exclude={"revision"}, exclude_unset=True)
    for field in ("title", "idea", "genre", "core_action", "success_condition"):
        if field in changes and isinstance(changes[field], str):
            changes[field] = changes[field].strip()
    current = store.get(principal.user_id, draft_id)
    if current is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_studio_draft_not_found")
    if not _step_is_complete(current, changes):
        raise coded(status.HTTP_400_BAD_REQUEST, "game_studio_step_incomplete")
    try:
        updated = store.update(principal.user_id, draft_id, body.revision, changes)
    except store.DraftConflict as exc:
        raise coded(status.HTTP_409_CONFLICT, str(exc))
    if updated is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_studio_draft_not_found")
    return updated
