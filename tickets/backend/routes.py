"""Authenticated REST API for internal tickets and their immutable comments."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

from . import permissions, service
from .models import (
    TicketCommentCreate,
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
)
from . import attachments
from .attachment_routes import router as attachment_router
from .notification_routes import router as notification_router
from .operations_routes import router as operations_router
from .team_routes import router as team_router

router = APIRouter()
router.include_router(team_router)
router.include_router(attachment_router)
router.include_router(notification_router)
router.include_router(operations_router)
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _error(exc: service.TicketServiceError):
    codes = {
        "ticket_not_found": (status.HTTP_404_NOT_FOUND, "ticket_not_found"),
        "invalid_status_transition": (status.HTTP_409_CONFLICT, "invalid_status_transition"),
        "invalid_ticket_reference": (status.HTTP_400_BAD_REQUEST, "invalid_ticket_reference"),
    }
    http_status, code = codes.get(exc.code, (status.HTTP_400_BAD_REQUEST, exc.code))
    return coded(http_status, code)


def _ticket_row(ticket_id: str):
    with db() as conn:
        return conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()


def _require_existing(ticket_id: str):
    row = _ticket_row(ticket_id)
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "ticket_not_found")
    return row


@router.get("/tickets")
def list_route(
    auth: Auth,
    status_filter: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    team_id: str | None = None,
    assigned_to: str | None = None,
    project_id: str | None = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
    overdue: bool | None = None,
    due_before: str | None = None,
    sort: str = "updated_at",
    direction: str = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del auth
    return service.list_tickets(
        status=status_filter, priority=priority, team_id=team_id, assigned_to=assigned_to,
        project_id=project_id, query=query, overdue=overdue, due_before=due_before,
        sort=sort, direction=direction, limit=limit, offset=offset,
    )


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_route(auth: Auth, body: TicketCreate) -> dict:
    try:
        return service.create_ticket(body, auth)
    except service.TicketServiceError as exc:
        raise _error(exc)


@router.get("/tickets/{ticket_id}")
def get_route(auth: Auth, ticket_id: str) -> dict:
    del auth
    ticket = service.get_ticket(ticket_id)
    if ticket is None:
        raise coded(status.HTTP_404_NOT_FOUND, "ticket_not_found")
    ticket["comments"] = service.list_comments(ticket_id)
    ticket["events"] = service.list_events(ticket_id)
    ticket["attachments"] = attachments.list_attachments(ticket_id)
    return ticket


@router.patch("/tickets/{ticket_id}")
def update_route(auth: Auth, ticket_id: str, body: TicketUpdate) -> dict:
    row = _require_existing(ticket_id)
    with db() as conn:
        allowed = permissions.can_update_ticket(conn, row, auth)
    if not allowed:
        raise coded(status.HTTP_403_FORBIDDEN, "ticket_update_forbidden")
    try:
        return service.update_ticket(ticket_id, body, auth)
    except service.TicketServiceError as exc:
        raise _error(exc)


@router.get("/tickets/{ticket_id}/comments")
def comments_route(
    auth: Auth,
    ticket_id: str,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    del auth
    _require_existing(ticket_id)
    return service.list_comments(ticket_id, limit=limit, offset=offset)


@router.post("/tickets/{ticket_id}/comments", status_code=status.HTTP_201_CREATED)
def comment_route(auth: Auth, ticket_id: str, body: TicketCommentCreate) -> dict:
    _require_existing(ticket_id)
    try:
        return service.add_comment(ticket_id, body.body, auth)
    except service.TicketServiceError as exc:
        raise _error(exc)
