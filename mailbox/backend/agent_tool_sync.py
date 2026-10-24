"""Mailbox-Werkzeuge am Projekt-Agenten passend zu den Freigaben (Befund 23.10.2026).

Der Kern hängt Modul-Werkzeuge mit ``default_agent_tools`` nur an Master-Agenten. Ein Projekt-Agent (auch der
Rechts-Agent) bekäme sie trotz Freigabe nie. Deshalb gleicht die Mailbox selbst ab: höchste Stufe aller Freigaben
eines Projekts → genau diese Werkzeuge am Projekt-Agenten; ohne Freigabe werden sie wieder entfernt. Andere Werkzeuge
des Agenten bleiben unberührt. Fehler werden geloggt und nie an die Freigabe weitergereicht.
"""
from __future__ import annotations

import logging

from hydrahive.db.connection import db

log = logging.getLogger("hydrahive.modules.mailbox")

READ = ("mailbox_accounts", "mailbox_search", "mailbox_read", "mailbox_attachment")
DRAFT = ("mailbox_draft", "mailbox_move", "mailbox_flag")
_BY_LEVEL = {"read": READ, "draft": READ + DRAFT}
_ALL = set(READ + DRAFT)


def _level(project_id: str) -> str | None:
    with db() as c:
        levels = {r[0] for r in c.execute("SELECT level FROM module_mailbox_shares WHERE target=?",
                                          (f"project:{project_id}",))}
    return "draft" if "draft" in levels else ("read" if levels else None)


def sync_project(project_id: str) -> None:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects._config_io import get as get_project
    from hydrahive.tools import REGISTRY
    try:
        project = get_project(project_id)
        agent = agent_config.get(project.get("agent_id") or "") if project else None
        if not agent:
            return
        want = [t for t in _BY_LEVEL.get(_level(project_id) or "", ()) if t in REGISTRY]
        current = list(agent.get("tools") or [])
        new = [t for t in current if t not in _ALL] + want
        if new != current:
            agent_config.update(agent["id"], tools=new)
            log.info("mailbox: Werkzeuge des Projekt-Agenten %s angepasst: %s", agent["id"], want or "keine")
    except Exception:  # noqa: BLE001 - eine Freigabe darf nie an einem Agenten scheitern
        log.exception("mailbox: Werkzeuge für Projekt %s nicht abgeglichen", project_id)


def sync_target(target: str) -> None:
    if target.startswith("project:"):
        sync_project(target.removeprefix("project:"))


def sync_all() -> None:
    """Beim Laden des Moduls: Freigaben aus älteren Versionen bekommen ihre Werkzeuge nachgetragen."""
    with db() as c:
        targets = {r[0] for r in c.execute("SELECT DISTINCT target FROM module_mailbox_shares")}
    for t in sorted(targets):
        sync_target(t)
