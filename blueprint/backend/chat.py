"""Chat neben dem Board (Etappe 3b): eine Sitzung je Board mit dem Projekt-Agenten.

Nach dem Vorbild von Game Studio und Storyteller: Die Oberfläche bettet die
Chatansicht des Kerns ein, dieses Modul sucht nur den Agenten aus und legt die
Sitzung an (oder nimmt die vorhandene). Die Sitzung trägt ``embedded_in``, damit
das Projekt-Cockpit sie nicht von selbst öffnet.

Der Kern gibt Sitzungs-Metadaten nicht an den Agenten weiter, und die Chatansicht
kennt keinen vorbelegten Text (am 12.11.2026 im Kern nachgelesen). Deshalb liefert
``start`` einen Einstiegstext mit Board, Idee und Werkzeugen, den der Nutzer in
seine erste Nachricht übernimmt.

Boards ohne Projekt haben keinen Chat. Vorgesehen war dort der Buddy des Nutzers.
Eine neue Sitzung mit dem Buddy würde aber auf der Buddy-Seite zur aktuellen
Unterhaltung, solange dort keine gemerkt ist. Verhindern lässt sich das nur im Kern.
"""
from __future__ import annotations

from hydrahive.db.connection import db

from . import access
from .store import BoardError

BOARD_KEY = "blueprint_board"  # Kennzeichen in session.metadata: zu welchem Board die Sitzung gehört
EMBED = {"embedded_in": "blueprint"}
# Was der Agent für die Arbeit am Board braucht. idea_read zählt nur, wenn das Ideen-Modul installiert ist.
TOOLS = ("blueprint_read", "blueprint_propose", "idea_read")
_IDEAS = "module_scratchpad_ideas"
_REASONS = {"missing": "project_missing", "read_only": "read_only"}
_ERRORS = {"no_project": "board_without_project", "project_missing": "project_unavailable",
           "no_agent": "project_agent_missing", "read_only": "project_read_only"}


def _one_line(value: object, limit: int = 200) -> str:
    return " ".join(str(value or "").split())[:limit]


def _agent(project: dict | None) -> dict | None:
    from hydrahive.agents import config as agent_config

    agent_id = (project or {}).get("agent_id")
    return agent_config.get(agent_id) if agent_id else None


def _missing_tools(agent: dict) -> list[str]:
    from hydrahive.tools import REGISTRY

    have = set(agent.get("tools") or [])
    return [name for name in TOOLS if name in REGISTRY and name not in have]


def describe(username: str, role: str, board: dict) -> dict:
    """Wer neben diesem Board antwortet, ob der Nutzer starten darf und welche Werkzeuge dem Agenten fehlen.

    ``reason`` nennt, warum es keinen Chat gibt: ``no_project``, ``project_missing`` (kein Zugriff
    oder gelöscht), ``no_agent`` oder ``read_only``. ``None``, wenn der Nutzer starten darf.
    """
    if not board.get("project_id"):
        return {"agent": None, "reason": "no_project", "can_start": False, "tools_missing": []}
    project, state = access.project_state(username, role, board["project_id"])
    agent = _agent(project)
    reason = _REASONS.get(state) or (None if agent else "no_agent")
    return {
        "agent": {"id": agent["id"], "name": agent["name"]} if agent else None,
        "reason": reason, "can_start": reason is None,
        "tools_missing": _missing_tools(agent) if agent else [],
    }


def linked_idea(username: str, board_id: int) -> dict | None:
    """Die eigene Idee, aus der das Board entstanden ist. ``None`` ohne Ideen-Modul oder ohne Idee."""
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (_IDEAS,)).fetchone()
        if not exists:
            return None
        row = conn.execute(
            f"SELECT id, title FROM {_IDEAS} WHERE username = ? AND board_id = ? ORDER BY id LIMIT 1",
            (username, board_id),
        ).fetchone()
    return {"id": row["id"], "title": _one_line(row["title"])} if row else None


def intro(board: dict, idea: dict | None) -> str:
    """Einstiegstext für die erste Nachricht. Namen sind Nutzertext: einzeilig und gekürzt."""
    lines = [f"Ich arbeite im Blueprint am Board „{_one_line(board['name'], 120)}“ (ID {board['id']})."]
    if idea:
        lines.append(f"Es gehört zur Idee „{idea['title']}“ (idea_id {idea['id']}); lies sie mit idea_read.")
    lines.append(
        "Lies das Board mit blueprint_read. Einen Entwurf legst du mit blueprint_propose ab: "
        "Hat das Board schon Inhalt, entsteht ein Vorschlag, den ich im Board übernehme oder verwerfe."
    )
    return "\n".join(lines) + "\n\nMeine Bitte: "


def _session(username: str, agent_id: str, project_id: str, board_id: int):
    from hydrahive.db import sessions as sessions_db

    return next(
        (
            session for session in sessions_db.list_for_user(username, limit=500)
            if session.agent_id == agent_id and session.project_id == project_id
            and session.metadata.get(BOARD_KEY) == board_id
        ),
        None,
    )


def start(username: str, role: str, board: dict) -> dict:
    """Sitzung zu diesem Board holen oder anlegen. ``BoardError`` mit Code, wenn es keinen Chat gibt."""
    from hydrahive.db import sessions as sessions_db

    info = describe(username, role, board)
    if info["reason"]:
        raise BoardError(_ERRORS[info["reason"]])
    agent, project_id = info["agent"], board["project_id"]
    session = _session(username, agent["id"], project_id, board["id"])
    reused = session is not None
    if reused:
        sessions_db.touch(session.id)  # nach vorn: die Chatansicht lädt nur die neuesten Sitzungen
    else:
        session = sessions_db.create(
            agent_id=agent["id"], user_id=username, project_id=project_id,
            title=f"Blueprint: {_one_line(board['name'], 120)}", metadata={BOARD_KEY: board["id"], **EMBED},
        )
    return {
        "session_id": session.id, "reused": reused, "agent": agent,
        "intro": intro(board, linked_idea(username, board["id"])),
    }
