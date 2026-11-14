"""Modell des Labor-Agenten über das Agenten-Template (Kern: Spec agent-templates.md, Plan E5).

Das Modul bringt im Manifest das Template `labor` mit (Kopie von `modul-schnell`, der Admin passt es auf der LLM-Seite
an). Der Labor-Agent wird daran gebunden; der Assistent zeigt nur das Primärmodell. Innerhalb der Kette wechselt man
im Chat wie bei jedem Projekt. Ohne Templates im Kern (älterer Kern) gilt das alte Verhalten: freie Modellwahl.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

TEMPLATES = ("labor", "modul-schnell")       # eigenes Template; fehlt es (Kern ohne Manifest-Templates) → modul-schnell


def template_or_none() -> str | None:
    try:
        from hydrahive.agents._binding import template_if_available
    except ImportError:
        return None
    return next((t for t in (template_if_available(x) for x in TEMPLATES) if t), None)


def primary() -> str:
    tid = template_or_none()
    if not tid:
        return ""
    from hydrahive.agents.templates import resolve_role
    t = resolve_role(tid)
    return t.chain[0] if t and t.chain else ""


def bind_existing(agent_id: str | None, module: str) -> bool:
    """Einmalig/idempotent: den vorhandenen Labor-Agenten ohne Template binden. Fehler nur loggen."""
    tid = template_or_none()
    if not tid or not agent_id:
        return False
    from hydrahive.agents import config as agent_config
    try:
        agent = agent_config.get(agent_id)
        if agent and not agent.get("template"):
            agent_config.update(agent_id, template=tid, _managed_by=module)
            logger.info("Hydra-Labor: Agent %s an Template %s gebunden", agent_id, tid)
            return True
    except Exception:
        logger.exception("Hydra-Labor: Agent %s nicht an %s gebunden", agent_id, tid)
    return False
