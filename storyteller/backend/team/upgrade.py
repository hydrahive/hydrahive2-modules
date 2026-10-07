"""Schreib-Teams älterer Storyteller-Versionen beim Öffnen des Buchs auf die aktuelle Team-Version ziehen (T1d).

Nur Projekte mit ``metadata.storyteller`` und kleinerer ``team_version``. Angepasst werden nur die Agenten des
Teams: der Projekt-Agent (Autor) und die freigegebenen Spezialisten, deren Name auf „— <Rolle>“ endet. Werkzeuge und
Anweisungen werden auf den Stand der Rolle gesetzt (eigene Änderungen an der Anweisung gehen dabei verloren – das
Verfeinern je Buch kommt mit Task 3579a9c7). Modell, Name und alles andere bleiben.
"""
from __future__ import annotations

import logging

from . import AUTHOR, HELPERS, TEAM_VERSION, available_tools, prompt_for
from .setup import _installed_tools

logger = logging.getLogger(__name__)


def _book_title(project: dict) -> str:
    return project.get("name") or ""


def _apply(project: dict) -> None:
    from hydrahive.agents import config as agent_config
    title, installed = _book_title(project), _installed_tools()
    by_suffix = {f"— {r.name}": r for r in HELPERS}
    ids: dict[str, str] = {}
    for hid in project.get("allowed_specialists") or []:
        agent = agent_config.get(hid)
        role = next((r for suffix, r in by_suffix.items() if (agent or {}).get("name", "").endswith(suffix)), None)
        if agent is None or role is None or agent.get("project_id") != project["id"]:
            continue
        agent_config.update(hid, tools=available_tools(role, installed))
        agent_config.set_system_prompt(hid, prompt_for(role, book_title=title))
        ids[role.key] = hid
    if project.get("agent_id"):
        agent_config.update(project["agent_id"], tools=available_tools(AUTHOR, installed))
        agent_config.set_system_prompt(project["agent_id"], prompt_for(AUTHOR, book_title=title, team_ids=ids))


def ensure_current(project_id: str) -> bool:
    """True, wenn das Team gerade nachgezogen wurde. Fehler werden geloggt (Öffnen darf nicht scheitern)."""
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id)
    meta = ((project or {}).get("metadata") or {}).get("storyteller")
    if not isinstance(meta, dict) or int(meta.get("team_version") or 0) >= TEAM_VERSION:
        return False
    try:
        _apply(project)
        project_config.update(project_id, metadata={**project["metadata"],
                                                    "storyteller": {**meta, "team_version": TEAM_VERSION}})
    except Exception:
        logger.exception("Schreib-Team in Projekt %s konnte nicht nachgezogen werden", project_id)
        return False
    logger.info("Schreib-Team in Projekt %s auf Version %d nachgezogen", project_id, TEAM_VERSION)
    return True
