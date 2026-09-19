"""Operations endpoints for ticket dashboards and saved views."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import bulk, dashboard, escalation, sla_profiles, views
from .models import BulkUpdateRequest, SavedViewCreate, SavedViewUpdate, SlaProfileCreate, SlaProfileUpdate
from .permissions import is_admin

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _require_admin(auth: AuthPrincipal) -> None:
    if not is_admin(auth):
        raise coded(status.HTTP_403_FORBIDDEN, "admin_required")


@router.get("/dashboard")
def dashboard_route(auth: Auth) -> dict:
    escalation.evaluate_escalations()
    return dashboard.dashboard_summary(auth)


@router.get("/sla/profiles")
def list_sla_profiles(auth: Auth) -> list[dict]:
    _require_admin(auth)
    return sla_profiles.list_profiles()


@router.post("/sla/profiles", status_code=status.HTTP_201_CREATED)
def create_sla_profile(auth: Auth, body: SlaProfileCreate) -> dict:
    _require_admin(auth)
    try:
        return sla_profiles.create_profile(body)
    except ValueError as exc:
        raise coded(status.HTTP_409_CONFLICT, str(exc))


@router.patch("/sla/profiles/{profile_id}")
def update_sla_profile(auth: Auth, profile_id: str, body: SlaProfileUpdate) -> dict:
    _require_admin(auth)
    try:
        return sla_profiles.update_profile(profile_id, body)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "sla_profile_not_found")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("/saved-views")
def list_saved_views(auth: Auth) -> list[dict]:
    return views.list_views(auth)


@router.post("/bulk-update")
def bulk_update(auth: Auth, body: BulkUpdateRequest) -> dict:
    try:
        return bulk.update_tickets(auth, body.ticket_ids, body.update)
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))


@router.post("/saved-views", status_code=status.HTTP_201_CREATED)
def create_saved_view(auth: Auth, body: SavedViewCreate) -> dict:
    try:
        return views.create_view(
            auth,
            name=body.name,
            filters=body.filters,
            sort=body.sort,
            direction=body.direction,
            team_id=body.team_id,
        )
    except PermissionError:
        raise coded(status.HTTP_403_FORBIDDEN, "saved_view_forbidden")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))


@router.patch("/saved-views/{view_id}")
def update_saved_view(auth: Auth, view_id: str, body: SavedViewUpdate) -> dict:
    try:
        return views.update_view(view_id, body, auth)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "saved_view_not_found")
    except PermissionError:
        raise coded(status.HTTP_403_FORBIDDEN, "saved_view_forbidden")
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_view(auth: Auth, view_id: str) -> None:
    try:
        views.delete_view(view_id, auth)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "saved_view_not_found")
    except PermissionError:
        raise coded(status.HTTP_403_FORBIDDEN, "saved_view_forbidden")
