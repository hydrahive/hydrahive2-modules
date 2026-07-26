from __future__ import annotations

from hydrahive.api.middleware.users import get_by_id
from hydrahive.tools.base import ToolContext, ToolResult

from .errors import MediacenterError


def username_for(ctx: ToolContext) -> str | None:
    user = get_by_id(ctx.user_id)
    return user["username"] if user else None


def failure(exc: Exception) -> ToolResult:
    if isinstance(exc, MediacenterError):
        return ToolResult.fail(exc.code)
    return ToolResult.fail("mediacenter_internal_error")
