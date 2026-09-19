"""Operations endpoints for ticket dashboards and saved views."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import dashboard, views
from .models import SavedViewCreate

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


@router.get("/dashboard")
def dashboard_route(auth: Auth) -> dict:
    return dashboard.dashboard_summary(auth)


@router.get("/saved-views")
def list_saved_views(auth: Auth) -> list[dict]:
    return views.list_views(auth)


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


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_view(auth: Auth, view_id: str) -> None:
    try:
        views.delete_view(view_id, auth)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "saved_view_not_found")
    except PermissionError:
        raise coded(status.HTTP_403_FORBIDDEN, "saved_view_forbidden")
