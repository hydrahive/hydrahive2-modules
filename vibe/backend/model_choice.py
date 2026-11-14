"""Modell eines Vibe-Projekts über das Agenten-Template (Kern: Spec agent-templates.md, Option B).

Der Vibe-Agent ist an das Template `modul-schnell` gebunden. Wählbar sind nur die Modelle seiner Kette (Primär,
Failover, Notfall); die Wahl gilt als Sitzungsmodell (`model_override`) des Vibe-Chats, das Template bleibt als
Failover dahinter. Ohne Templates im Kern (älterer Kern) gilt das alte Verhalten: Modell direkt am Agenten.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

TEMPLATE = "modul-schnell"
_ROLES = ("Primär", "Failover", "Notfall")


def template_or_none() -> str | None:
    """`modul-schnell`, wenn der Kern Templates kennt und es eine nutzbare Kette hat, sonst None."""
    try:
        from hydrahive.agents._binding import template_if_available
    except ImportError:
        return None
    return template_if_available(TEMPLATE)


def chain_of(agent: dict | None) -> list[str]:
    """Kette des gebundenen Agenten; ohne Bindung leer."""
    if not agent or not agent.get("template"):
        return []
    from hydrahive.agents.templates import resolve
    t = resolve(agent)
    return list(t.chain) if t else []


def template_chain() -> list[str]:
    tid = template_or_none()
    if not tid:
        return []
    from hydrahive.agents.templates import resolve_role
    t = resolve_role(tid)
    return list(t.chain) if t else []


def items(chain: list[str]) -> list[dict]:
    return [{"id": m, "label": m, "provider": _ROLES[min(i, 2)]} for i, m in enumerate(chain)]


def current(agent: dict, sid: str | None) -> str:
    """Wirksames Modell: Sitzungsmodell aus der Kette, sonst Primär. Ungebunden: Modell des Agenten."""
    chain = chain_of(agent)
    if not chain:
        return str(agent.get("llm_model") or "")
    if sid:
        from hydrahive.db import sessions as sessions_db
        s = sessions_db.get(sid)
        chosen = ((s.metadata or {}) if s else {}).get("model_override")
        if chosen in chain:
            return chosen
    return chain[0]


def set_session_model(sid: str, chain: list[str], model: str) -> None:
    """Primär = kein Override (Template entscheidet), sonst Override aus der Kette."""
    from hydrahive.db import sessions as sessions_db
    sessions_db.set_model_override(sid, None if model == chain[0] else model)


def bind_existing(module: str) -> int:
    """Einmalig/idempotent: Vibe-Agenten ohne Template an `modul-schnell` binden. Fehler nur loggen."""
    tid = template_or_none()
    if not tid:
        return 0
    from hydrahive.agents import config as agent_config

    from . import state
    n = 0
    for row in state.all_rows():
        try:
            agent = agent_config.get(row["agent_id"])
            if agent and not agent.get("template"):
                agent_config.update(row["agent_id"], template=tid, _managed_by=module)
                n += 1
        except Exception:
            logger.exception("Vibe: Agent %s nicht an %s gebunden", row.get("agent_id"), tid)
    if n:
        logger.info("Vibe: %d Agenten an Template %s gebunden", n, tid)
    return n
