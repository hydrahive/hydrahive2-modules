"""Native internal HydraHive ticket module."""
from __future__ import annotations

from .routes import router
from .tools.read import LIST_TOOL, READ_TOOL
from .tools.write import COMMENT_TOOL, CREATE_TASK_TOOL, CREATE_TOOL, UPDATE_TOOL
from .tools.github import GITHUB_ISSUE_TOOL, GITHUB_LINK_TOOL, GITHUB_PROJECT_ITEMS_TOOL, GITHUB_PROJECT_LIST_TOOL, GITHUB_UNLINK_TOOL


def register(ctx) -> None:
    """Register API routes, migrations, and the agent-facing ticket tools."""
    ctx.register_router(router)
    for tool in (LIST_TOOL, READ_TOOL, CREATE_TOOL, COMMENT_TOOL, UPDATE_TOOL, CREATE_TASK_TOOL, GITHUB_PROJECT_LIST_TOOL, GITHUB_PROJECT_ITEMS_TOOL, GITHUB_ISSUE_TOOL, GITHUB_LINK_TOOL, GITHUB_UNLINK_TOOL):
        ctx.register_tool(tool)
    ctx.register_migrations("migrations")
