"""Vibe-Projekte anlegen und entfernen (PLAN-V1.md Baustein 4; Muster hydralabor/backend/lab_project.py).

Reihenfolge beim Anlegen: Netz → Container → Kern-Projekt (legt den Projekt-Agenten mit an) → Ausführung im Container
(K1, prüft dass der Container da ist) → Agent umbauen (Name, Werkzeuge, Skills, Prompt) → `managed_by = vibe` →
Datenzeile. Geht etwas schief, wird alles Eigene wieder abgeräumt. Entfernt wird NUR, was die Vibe-Markierung am
Kern-Projekt trägt UND in der eigenen Tabelle steht – ein fremdes Projekt fasst Vibe nie an.
"""
from __future__ import annotations

import logging

from . import agent_profile, container, network, skill_sync, state

logger = logging.getLogger(__name__)
MODULE = "vibe"
_MARK = {"project": True}
MAX_NAME = 60


class VibeProjectError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _clean_name(name: str) -> str:
    if not isinstance(name, str):
        raise VibeProjectError("vibe_name_invalid")
    n = name.strip()
    if not n or len(n) > MAX_NAME or any(ord(c) < 32 or c in "<>" for c in n) or ".." in n or "/" in n or "\\" in n:
        raise VibeProjectError("vibe_name_invalid")
    return n


def _check_model(model: str) -> None:
    from hydrahive.agents._validation import AgentValidationError, validate_model
    if not isinstance(model, str) or not model.strip():
        raise VibeProjectError("vibe_model_unavailable")
    try:
        validate_model(model)
    except AgentValidationError:
        raise VibeProjectError("vibe_model_unavailable") from None


def _build_agent(aid: str, pid: str, admin: str) -> None:
    from hydrahive.agents import _managed
    from hydrahive.agents import config as agent_config
    agent_config.update(aid, name="Vibe-Agent", tools=list(agent_profile.TOOLS), mcp_servers=[],
                        description="Baut Apps im Vibe-Container. Werkzeuge fest.",
                        disabled_skills=agent_profile.disabled_skills(aid, admin, pid))
    agent_config.set_system_prompt(aid, agent_profile.system_prompt())
    _managed.set_managed(aid, MODULE)                       # zuletzt: davor sind die Änderungen noch erlaubt


def _limits(limits: container.Limits | None) -> container.Limits:
    return limits or container.Limits()


async def _cleanup(pid: str | None, made_container: bool) -> None:
    """Räumt alles Eigene ab. Jeder Schritt für sich abgesichert: scheitert einer (echte Probe 5.11.: Tabelle fehlte),
    laufen die übrigen trotzdem. Der Fehler, der das Aufräumen ausgelöst hat, bleibt der gemeldete."""
    from hydrahive.projects import config as project_config
    if pid:
        for label, step in (("Projekt", lambda: project_config.delete(pid)), ("Datenzeile", lambda: state.delete_row(pid))):
            try:
                step()
            except Exception:                                # noqa: BLE001 – Aufräumen darf nie den ersten Fehler verdecken
                logger.exception("Vibe: %s von %s ließ sich nicht abräumen", label, pid)
    if made_container and pid:
        try:
            await container.remove(pid)
        except Exception:                                    # noqa: BLE001
            logger.exception("Vibe: Container von %s ließ sich nicht entfernen", pid)
    try:
        await network.remove_if_unused()
    except Exception:                                        # noqa: BLE001
        logger.exception("Vibe: Netz ließ sich nicht abräumen")


async def create(*, admin: str, name: str, model: str, limits: container.Limits | None = None) -> dict:
    """Legt Projekt, Agent und Container an. Läuft in der Ereignisschleife des Servers (Aufrufer: Hintergrund-Auftrag);
    eine synchrone Hülle mit asyncio.run() bricht dort mit „cannot be called from a running event loop“ ab."""
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    from hydrahive.skills.loader import install_system_defaults
    limits = _limits(limits)
    clean = _clean_name(name)
    _check_model(model)
    install_system_defaults()
    skill_sync.install()
    pid: str | None = None
    made_container = False
    try:
        project = project_config.create(clean, description="Vibe-Projekt: eine App, gebaut im Chat. Alle Befehle laufen "
                                        "im abgeschotteten Container.", members=[], llm_model=model, created_by=admin,
                                        metadata={MODULE: dict(_MARK)})
        pid, aid = project["id"], project["agent_id"]
        await network.ensure_network()
        await container.launch(pid, limits)
        made_container = True
        execution.set_container(pid, container.name_for(pid), actor=admin)
        _build_agent(aid, pid, admin)
        state.add_row(project_id=pid, agent_id=aid, container=container.name_for(pid), name=clean, owner=admin)
    except Exception:
        logger.exception("Vibe: Projekt unvollständig – räume ab")
        await _cleanup(pid, made_container)
        raise VibeProjectError("vibe_project_failed") from None
    logger.info("Vibe: Projekt %s, Agent %s angelegt", pid, aid)
    return {"project_id": pid, "agent_id": aid}


async def remove(project_id: str, *, owner: str) -> None:
    """Nur ein eigenes Vibe-Projekt entfernen: Datenzeile des Nutzers UND Markierung am Kern-Projekt nötig."""
    from hydrahive.projects import config as project_config
    row = state.get_row(project_id)
    if row is None:
        return
    if row["owner"] != owner:
        raise VibeProjectError("vibe_project_not_found")
    p = project_config.get(project_id)
    if p is None or (p.get("metadata") or {}).get(MODULE) != _MARK:
        return
    project_config.delete(project_id)
    state.delete_row(project_id)
    await container.remove(project_id)
    await network.remove_if_unused()
