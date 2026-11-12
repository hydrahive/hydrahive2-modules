"""Gemeinsame Konstanten und Helfer der Ideen-Tests."""
from __future__ import annotations

from pathlib import Path

MOD_PREFIX = "/api/modules/scratchpad"
PROJECT_A = "ideen-projekt-alice"
PROJECT_B = "ideen-projekt-bob"
TABLES = ("module_scratchpad_ideas", "module_scratchpad_idea_notes")


def make_ctx(username: str = "alice", project_id: str | None = None):
    from hydrahive.tools.base import ToolContext

    return ToolContext(
        session_id="sess-1", agent_id="agent-1", user_id=username,
        workspace=Path("/tmp"), project_id=project_id,
    )
