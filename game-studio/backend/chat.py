"""Chat sessions with the project agent, embedded in the Game Studio workspace."""

from __future__ import annotations

PROJECT_KEY = "game_studio_project"
EMBED = {"embedded_in": "game-studio"}


def project_agent(config: dict) -> dict | None:
    from hydrahive.agents import config as agent_config

    agent_id = config.get("agent_id")
    return agent_config.get(agent_id) if agent_id else None


def _existing_session(username: str, agent_id: str, project_id: str):
    from hydrahive.db import sessions as sessions_db

    return next(
        (
            session
            for session in sessions_db.list_for_user(username, limit=500)
            if session.agent_id == agent_id
            and session.project_id == project_id
            and session.metadata.get(PROJECT_KEY) == project_id
        ),
        None,
    )


def info(config: dict, can_write: bool) -> dict:
    agent = project_agent(config)
    return {
        "agent": {"id": agent["id"], "name": agent["name"]} if agent else None,
        "can_start": bool(agent) and can_write,
    }


def start(config: dict, username: str) -> dict | None:
    from hydrahive.db import sessions as sessions_db

    agent = project_agent(config)
    if not agent:
        return None
    project_id = config["id"]
    session = _existing_session(username, agent["id"], project_id)
    reused = session is not None
    if reused:
        sessions_db.touch(session.id)
    else:
        session = sessions_db.create(
            agent_id=agent["id"],
            user_id=username,
            project_id=project_id,
            title=f"Game Studio: {config.get('name', project_id)}"[:200],
            metadata={PROJECT_KEY: project_id, **EMBED},
        )
    return {
        "session_id": session.id,
        "reused": reused,
        "agent": {"id": agent["id"], "name": agent["name"]},
    }
