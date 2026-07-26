from __future__ import annotations

from hydrahive.api.middleware.users import get_by_username
from hydrahive.tools.base import ToolContext, ToolResult

from .errors import MediacenterError


def principal_for(ctx: ToolContext) -> dict | None:
    """Resolve the runner's username to the current immutable user principal.

    ``ToolContext.user_id`` is legacy-named and currently carries the session
    username.  Mediacenter ownership must still use the stable principal ID so
    deleting and recreating the same username cannot inherit old media data.
    """
    return get_by_username(ctx.user_id)


def failure(exc: Exception) -> ToolResult:
    if isinstance(exc, MediacenterError):
        return ToolResult.fail(exc.code)
    return ToolResult.fail("mediacenter_internal_error")
