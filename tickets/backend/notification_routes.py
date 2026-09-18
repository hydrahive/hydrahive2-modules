"""Authenticated internal notification polling routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

from . import notifications

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


@router.get("/notifications")
def list_notifications_route(
    auth: Auth,
    unread_only: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict]:
    return notifications.list_for_user(auth.user_id, unread_only=unread_only, limit=limit)


@router.post("/notifications/{notification_id}/read")
def read_notification_route(auth: Auth, notification_id: str) -> dict:
    if not notifications.mark_read(auth.user_id, notification_id):
        raise coded(status.HTTP_404_NOT_FOUND, "notification_not_found")
    return {"read": True}
