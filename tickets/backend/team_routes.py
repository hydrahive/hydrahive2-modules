"""Authenticated team management routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import permissions, teams
from .models import TeamCreate, TeamMemberUpsert, TeamUpdate
from .service import TicketServiceError

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _error(exc: TicketServiceError):
    codes = {
        "team_not_found": (status.HTTP_404_NOT_FOUND, "team_not_found"),
        "team_name_taken": (status.HTTP_409_CONFLICT, "team_name_taken"),
        "user_not_found": (status.HTTP_404_NOT_FOUND, "user_not_found"),
    }
    http_status, code = codes.get(exc.code, (status.HTTP_400_BAD_REQUEST, exc.code))
    return coded(http_status, code)


def _team_row(team_id: str):
    with db() as conn:
        return conn.execute("SELECT * FROM module_ticket_teams WHERE id=?", (team_id,)).fetchone()


def _require_manager(team_id: str, auth: AuthPrincipal):
    row = _team_row(team_id)
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "team_not_found")
    with db() as conn:
        if not permissions.can_manage_team(conn, team_id, auth):
            raise coded(status.HTTP_403_FORBIDDEN, "team_manage_forbidden")


@router.get("/teams")
def list_teams_route(auth: Auth) -> list[dict]:
    del auth
    return teams.list_teams()


@router.post("/teams", status_code=status.HTTP_201_CREATED)
def create_team_route(auth: Auth, body: TeamCreate) -> dict:
    if not permissions.can_create_team(auth):
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
    try:
        return teams.create_team(body, auth)
    except TicketServiceError as exc:
        raise _error(exc)


@router.patch("/teams/{team_id}")
def update_team_route(auth: Auth, team_id: str, body: TeamUpdate) -> dict:
    _require_manager(team_id, auth)
    try:
        return teams.update_team(team_id, body)
    except TicketServiceError as exc:
        raise _error(exc)


@router.post("/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
def add_team_member_route(auth: Auth, team_id: str, body: TeamMemberUpsert) -> dict:
    _require_manager(team_id, auth)
    try:
        return teams.add_member(team_id, body)
    except TicketServiceError as exc:
        raise _error(exc)


@router.delete("/teams/{team_id}/members/{user_id}")
def remove_team_member_route(auth: Auth, team_id: str, user_id: str) -> dict:
    _require_manager(team_id, auth)
    if not teams.remove_member(team_id, user_id):
        raise coded(status.HTTP_404_NOT_FOUND, "team_member_not_found")
    return {"removed": True}
