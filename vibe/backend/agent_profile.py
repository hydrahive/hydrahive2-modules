"""Vibe-Agent: feste Werkzeuge, Skills und Prompt (PLAN-V1.md Baustein 4; Muster hydralabor/backend/agent_profile.py).

Werkzeuge: Teilmenge der Container-Allowlist des Kerns (runner/_project_tool_scope.CONTAINER_ALLOWED) ohne fetch_url –
Vibe braucht keine Abrufe mit Server-Zugangsdaten. Skills: nur `vibe-regeln`; alle Server-Skills werden ausgeblendet.
"""
from __future__ import annotations

from pathlib import Path

TOOLS: tuple[str, ...] = ("file_patch", "file_read", "file_write", "help_read", "help_search", "list_skills",
                          "load_skill", "read_memory", "search_memory", "shell_exec", "todo_write", "web_search",
                          "write_memory")
SKILLS = frozenset({"vibe-regeln"})
_PROMPT = Path(__file__).resolve().parents[1] / "agent" / "PROMPT.md"


def system_prompt() -> str:
    return _PROMPT.read_text(encoding="utf-8").strip()


def disabled_skills(agent_id: str, owner: str, project_id: str) -> list[str]:
    """Alle sichtbaren Skills außer den Vibe-Skills ausblenden."""
    from hydrahive.skills.loader import list_for_agent
    return sorted({s.name for s in list_for_agent(agent_id, owner, project_id=project_id)} - SKILLS)
