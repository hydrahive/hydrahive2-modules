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


def new_team_project(username: str, title: str, model: str) -> dict[str, Any]:
    """Projekt mit Autor + 7 Helfern, noch ohne Buch. Ergebnis: {project_id, author, helpers}.

    Scheitert ein Schritt, wird alles Angelegte wieder entfernt. Danach setzt der Aufrufer das Buch und mit
    ``mark_book_project`` die Metadaten (erst dann gilt das Projekt als Buch-Projekt)."""
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._defaults import (
        DEFAULT_MAX_TOKENS,
        DEFAULT_TEMPERATURE,
        DEFAULT_THINKING_BUDGET,
    )
    from hydrahive.projects import config as project_config
    installed = _installed_tools()
    project = project_config.create(title, description="Buch im Storyteller (eigenes Projekt mit Schreib-Team)",
                                    members=[], llm_model=model, created_by=username)
    pid, helper_ids = project["id"], []
    try:
        for role in HELPERS:
            helper = agent_config.create(
                agent_type="specialist", name=f"{title} — {role.name}"[:200], llm_model=model,
                tools=available_tools(role, installed), owner=username, created_by=project["agent_id"],
                description=role.description, temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS,
                thinking_budget=DEFAULT_THINKING_BUDGET, project_id=pid,
                system_prompt=prompt_for(role, book_title=title))
            helper_ids.append(helper["id"])
        ids = {role.key: hid for role, hid in zip(HELPERS, helper_ids)}
        agent_config.update(project["agent_id"], name=f"{title} — {AUTHOR.name}"[:200],
                            tools=available_tools(AUTHOR, installed), description=AUTHOR.description)
        agent_config.set_system_prompt(project["agent_id"], prompt_for(AUTHOR, book_title=title, team_ids=ids))
        project_config.update(pid, allowed_specialists=list(helper_ids))
    except Exception:
        drop_project(pid)
        raise
    return {"project_id": pid, "author": project["agent_id"], "helpers": ids}


def mark_book_project(project_id: str, book_id: str) -> None:
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id) or {}
    project_config.update(project_id, metadata={**(project.get("metadata") or {}),
                                                "storyteller": {"book_id": book_id, "team_version": TEAM_VERSION}})


def drop_project(project_id: str) -> None:
    """Halb angelegtes Projekt wieder entfernen – der Kern löscht Autor, Helfer (#527) und Arbeitsordner mit."""
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    for hid in (project_config.get(project_id) or {}).get("allowed_specialists") or []:
        agent_config.delete(hid)                  # falls der Kern noch ohne #527 läuft
    project_config.delete(project_id)


def check_model(model: str) -> None:
    """Vorab wie der Kern beim Anlegen der Agenten prüfen: ist das Modell nicht (mehr) in der Live-Liste, gäbe es sonst
    mitten im Anlegen einen AgentValidationError (HTTP 500). Leere Liste = Erst-Setup → durchwinken wie der Kern."""
    from hydrahive.agents._validation import AgentValidationError, validate_model
    try:
        validate_model(model)
    except AgentValidationError:
        raise StoryError("model_unavailable", 400, {"model": model}) from None


def create_book_project(username: str, fields: dict[str, Any], *, model: str = "") -> dict[str, Any]:
    _precheck(fields)
    use_model = (model or "").strip() or default_model()
    if not use_model:
        raise StoryError("no_model", 409)
    check_model(use_model)
    title = str(fields["title"]).strip()
    team = new_team_project(username, title, use_model)
    pid = team["project_id"]
    try:
        book = storage.create_book(pid, {**fields, "title": title, "model": use_model})
        mark_book_project(pid, book["id"])
    except Exception:
        logger.exception("Buch-Projekt '%s' konnte nicht vollständig angelegt werden – räume auf", title)
        drop_project(pid)
        raise
    logger.info("Buch-Projekt '%s' angelegt (projekt=%s, buch=%s)", title, pid, book["id"])
    return {"project_id": pid, "book": book, "team": {"author": team["author"], "helpers": team["helpers"]}}
