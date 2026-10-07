"""„Neues Buch“ als eigenes Projekt mit Schreib-Team anlegen (Spec schreib-team.md §4, Plan T1c).

Reihenfolge: Eingaben prüfen → Modell bestimmen → Projekt (der Kern legt den Projekt-Agenten mit an) → Buch →
Projekt-Agent wird zum Autor (Name, Werkzeuge, Anweisung) → 7 Helfer als Spezialisten, freigegeben im Projekt.
Scheitert ein Schritt, wird alles bereits Angelegte wieder entfernt (Projekt-Löschen räumt Autor + Workspace mit ab,
Helfer werden einzeln gelöscht). Die Rechte prüft die Route, nicht diese Funktion.
"""
from __future__ import annotations

import logging
from typing import Any

from .. import storage
from .._files import StoryError
from .._names import KINDS, LANGUAGES
from . import AUTHOR, HELPERS, TEAM_VERSION, available_tools, prompt_for

logger = logging.getLogger(__name__)


def default_model() -> str:
    """HydraHive-Standardmodell für Chats (Einstellungen → LLM). Leer, wenn keins gesetzt ist."""
    from hydrahive.llm._config import get_default
    return get_default("chat")


def _installed_tools() -> set[str]:
    from hydrahive.tools import REGISTRY
    return set(REGISTRY)


def _precheck(fields: dict[str, Any]) -> None:
    """Fehler, die das Buch sonst erst nach dem Projekt-Anlegen fände (Projekt bliebe sonst kurz leer stehen)."""
    if not str(fields.get("title") or "").strip():
        raise StoryError("title_required")
    if fields.get("kind") not in KINDS or fields.get("language", "de") not in LANGUAGES:
        raise StoryError("kind_or_language_invalid")


def create_book_project(username: str, fields: dict[str, Any], *, model: str = "") -> dict[str, Any]:
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._defaults import (
        DEFAULT_MAX_TOKENS,
        DEFAULT_TEMPERATURE,
        DEFAULT_THINKING_BUDGET,
    )
    from hydrahive.projects import config as project_config

    _precheck(fields)
    use_model = (model or "").strip() or default_model()
    if not use_model:
        raise StoryError("no_model", 409)
    title = str(fields["title"]).strip()
    installed = _installed_tools()

    project = project_config.create(title, description="Buch im Storyteller (eigenes Projekt mit Schreib-Team)",
                                    members=[], llm_model=use_model, created_by=username)
    pid, helper_ids = project["id"], []
    try:
        book = storage.create_book(pid, {**fields, "title": title, "model": use_model})
        for role in HELPERS:
            helper = agent_config.create(
                agent_type="specialist", name=f"{title} — {role.name}"[:200], llm_model=use_model,
                tools=available_tools(role, installed), owner=username, created_by=project["agent_id"],
                description=role.description, temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS,
                thinking_budget=DEFAULT_THINKING_BUDGET, project_id=pid,
                system_prompt=prompt_for(role, book_title=title))
            helper_ids.append(helper["id"])
        ids = {role.key: hid for role, hid in zip(HELPERS, helper_ids)}
        agent_config.update(project["agent_id"], name=f"{title} — {AUTHOR.name}"[:200],
                            tools=available_tools(AUTHOR, installed), description=AUTHOR.description)
        agent_config.set_system_prompt(project["agent_id"], prompt_for(AUTHOR, book_title=title, team_ids=ids))
        project_config.update(pid, allowed_specialists=list(helper_ids),
                              metadata={**(project.get("metadata") or {}),
                                        "storyteller": {"book_id": book["id"], "team_version": TEAM_VERSION}})
    except Exception:
        logger.exception("Buch-Projekt '%s' konnte nicht vollständig angelegt werden – räume auf", title)
        for hid in helper_ids:
            agent_config.delete(hid)
        project_config.delete(pid)
        raise
    logger.info("Buch-Projekt '%s' angelegt (projekt=%s, buch=%s, helfer=%d)", title, pid, book["id"], len(helper_ids))
    return {"project_id": pid, "book": book, "team": {"author": project["agent_id"], "helpers": ids}}
