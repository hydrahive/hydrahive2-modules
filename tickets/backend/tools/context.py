"""Resolve the legacy ToolContext user field to an immutable principal."""
from __future__ import annotations

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.users import get_by_id, get_by_username
from hydrahive.tools.base import ToolContext, ToolResult


def principal_for(ctx: ToolContext) -> AuthPrincipal | None:
    record = get_by_username(ctx.user_id) or get_by_id(ctx.user_id)
    if record is None:
        return None
    return AuthPrincipal(record["user_id"], record["username"], record["role"])


def invalid_principal() -> ToolResult:
    return ToolResult.fail("invalid_principal")


def invalid_request() -> ToolResult:
    return ToolResult.fail("ticket_request_invalid")


def service_failure(exc: Exception) -> ToolResult:
    from ..service import TicketServiceError

    if isinstance(exc, TicketServiceError):
        return ToolResult.fail(exc.code)
    return ToolResult.fail("ticket_internal_error")
