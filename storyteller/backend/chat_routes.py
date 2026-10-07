"""Storyteller — Chat mit dem Projekt-Agenten starten (Ghostwriter G4a, Spec §11.3).

Legt eine Kern-Chat-Sitzung mit dem Projekt-Agenten im Projekt an. Die erste Nachricht wird nicht gesendet;
die Antwort enthält einen Einstiegstext (Buch, Szene, Werkzeuge), den der Nutzer in den Chat übernimmt.
Rechte wie die Kern-Route POST /api/sessions: Schreibrecht im Projekt + Zugriff auf den Agenten.
"""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import proposals, storage
from ._files import project_access
from ._route_base import Auth, _call, _guard
from .agent_tools import TOOLS

router = APIRouter()
B = "/projects/{project_id}/books/{book_id}"
TOOL_NAMES = [t.name for t in TOOLS]


class ChatIn(BaseModel):
    scene_id: str | None = Field(default=None, max_length=64)


def _project_agent(project_id: str) -> tuple[dict | None, dict | None]:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    project = project_config.get(project_id)
    agent_id = (project or {}).get("agent_id")
    return project, (agent_config.get(agent_id) if agent_id else None)


def _intro(book: dict, scene: dict | None) -> str:
    where = f" Szene „{scene['title'] or scene['id']}“ (scene_id {scene['id']})" if scene else ""
    return (f"Ich arbeite im Storyteller am Buch „{book['title']}“ (book_id {book['id']}).{where}\n"
            "Lies zuerst mit storyteller_outline die Gliederung und mit storyteller_read die Szene. "
            "Neuen Text legst du nur mit storyteller_propose_text als Vorschlag ab – ich übernehme ihn im Storyteller.\n\n"
            "Meine Bitte: ")


@router.get(f"{B}/chat")
def chat_info(project_id: str, book_id: str, auth: Auth):
    """Projekt-Agent, fehlende Storyteller-Werkzeuge, ob der Nutzer starten darf."""
    _guard(auth, project_id, "read")
    _call(storage.get_book, project_id, book_id)
    _, agent = _project_agent(project_id)
    have = set((agent or {}).get("tools") or [])
    return {"agent": {"id": agent["id"], "name": agent["name"]} if agent else None,
            "tools_missing": [n for n in TOOL_NAMES if n not in have] if agent else TOOL_NAMES,
            "can_start": bool(agent) and project_access(auth[0], auth[1], project_id, "write") == "ok"}


@router.post(f"{B}/chat")
def chat_start(project_id: str, book_id: str, body: ChatIn, auth: Auth):
    _guard(auth, project_id)
    book = _call(storage.get_book, project_id, book_id)
    scene = _call(storage.get_scene, project_id, book_id, body.scene_id) if body.scene_id else None
    project, agent = _project_agent(project_id)
    if not agent:
        raise coded(status.HTTP_409_CONFLICT, "project_agent_missing")
    from hydrahive.api.routes._session_access import assert_agent_access
    from hydrahive.db import sessions as sessions_db
    assert_agent_access(agent, project, *auth)
    s = sessions_db.create(agent_id=agent["id"], user_id=auth[0], project_id=project_id,
                           title=f"Storyteller: {book['title']}"[:200])
    return {"session_id": s.id, "url": f"/werkstatt/{s.id}", "intro": _intro(book, scene),
            "agent": {"id": agent["id"], "name": agent["name"]}}


@router.get(f"{B}/proposals")
def list_proposals(project_id: str, book_id: str, auth: Auth):
    """Offene Vorschläge (Oberfläche fragt nach, solange der Chat-Modus offen ist)."""
    _guard(auth, project_id, "read")
    _call(storage.get_book, project_id, book_id)
    return proposals.list_for_book(project_id, book_id)
