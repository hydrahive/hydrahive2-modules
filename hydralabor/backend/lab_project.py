"""Projekt „Hydra-Labor“ + Labor-Agent (PLAN-L1.md Bausteine 4/5).

Reihenfolge: Projekt (legt den Projekt-Agenten mit an) → Ausführung im Container (K1, prüft dass hh-labor da ist)
→ Agent umbauen (Name, Werkzeuge, Skills, Prompt) → `managed_by = hydralabor`. Geht etwas schief, wird das eben
angelegte Projekt samt Agent wieder entfernt. Entfernt wird nur ein Projekt mit der Labor-Markierung.
"""
from __future__ import annotations

import logging

from . import agent_profile
from .container import NAME, LaborError

logger = logging.getLogger(__name__)
MODULE = "hydralabor"
PROJECT_NAME = "Hydra-Labor"
_MARK = {"lab": True}


def _check_model(model: str) -> None:
    from hydrahive.agents._validation import AgentValidationError, validate_model
    try:
        validate_model(model)
    except AgentValidationError:
        raise LaborError("labor_model_unavailable") from None


def create(*, admin: str, model: str) -> dict:
    _check_model(model)
    from hydrahive.agents import _managed
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    from hydrahive.skills.loader import install_system_defaults

    from . import skill_sync
    install_system_defaults()
    skill_sync.install()
    project = project_config.create(PROJECT_NAME, description="Labor zum Mitbauen an HydraHive (Modul Hydra-Labor). "
                                    "Alle Befehle laufen im abgeschotteten Container.", members=[],
                                    llm_model=model, created_by=admin, metadata={MODULE: dict(_MARK)})
    pid, aid = project["id"], project["agent_id"]
    try:
        execution.set_container(pid, NAME, actor=admin)
        agent_config.update(aid, name="Labor-Agent", tools=list(agent_profile.TOOLS), mcp_servers=[],
                            description="Arbeitet nur im Labor-Container (Hydra-Labor). Werkzeuge fest.",
                            disabled_skills=agent_profile.disabled_skills(aid, admin, pid))
        agent_config.set_system_prompt(aid, agent_profile.system_prompt())
        _managed.set_managed(aid, MODULE)
    except Exception:
        logger.exception("Hydra-Labor: Projekt unvollständig – räume %s ab", pid)
        project_config.delete(pid)
        raise LaborError("labor_project_failed") from None
    logger.info("Hydra-Labor: Projekt %s, Agent %s angelegt", pid, aid)
    return {"project_id": pid, "agent_id": aid}


def remove(made: dict) -> None:
    """Nur das Labor-Projekt (Markierung) löschen; der Kern entfernt dabei den Projekt-Agenten mit."""
    from hydrahive.projects import config as project_config
    pid = (made or {}).get("project_id") or ""
    p = project_config.get(pid) if pid else None
    if not p or (p.get("metadata") or {}).get(MODULE) != _MARK:
        return
    project_config.delete(pid)
