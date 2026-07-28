"""Voice-Modul E5 — LLM-Auswahl fürs Voicebox-Gespräch.

Setzt/liest einen model_override NUR auf der Voice-Session des eingeloggten
Users (dessen Master-Agent, channel='voice'). Der Master-Agent selbst bleibt
unverändert — der normale Chat ist nicht betroffen.

Nutzt bestehende Core-Infrastruktur:
- agent_config.list_by_owner(user) → Master-Agent finden
- sessions_db.get / set_model_override → Override lesen/setzen (read-modify-write)
- registry.list_models('chat') → Modell-Katalog fürs Dropdown
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.llm import registry

router = APIRouter()

VOICE_CHANNEL = "voice"


def _find_master(username: str) -> dict | None:
    for a in agent_config.list_by_owner(username):
        if a.get("type") == "master" and a.get("status") != "disabled":
            return a
    return None


def _voice_session_id(agent_id: str) -> str | None:
    """Neueste Voice-Session dieses (Master-)Agenten — read-only, legt keine an."""
    with db() as conn:
        row = conn.execute(
            """SELECT id FROM sessions
                WHERE agent_id = ? AND channel = ?
                ORDER BY updated_at DESC LIMIT 1""",
            (agent_id, VOICE_CHANNEL),
        ).fetchone()
    return row["id"] if row else None


@router.get("/llm")
def get_llm(auth: tuple = Depends(require_auth)):
    """Aktueller LLM-Zustand der Voicebox: Override (falls gesetzt) + Agent-Default."""
    username, _role = auth
    master = _find_master(username)
    if not master:
        return JSONResponse({"error": "no_master_agent"}, status_code=404)

    agent_default = master.get("llm_model") or ""
    sid = _voice_session_id(master["id"])
    override = None
    if sid:
        session = sessions_db.get(sid)
        if session:
            override = (session.metadata or {}).get("model_override")
    return {
        "override": override,
        "agent_default": agent_default,
        "has_session": sid is not None,
    }


@router.put("/llm")
async def put_llm(request: Request, auth: tuple = Depends(require_auth)):
    """Setzt (oder entfernt) das Voice-LLM. Leerer/kein model → zurück auf
    Agent-Standard. Wirkt nur auf die Voice-Session des eingeloggten Users."""
    username, _role = auth
    master = _find_master(username)
    if not master:
        return JSONResponse({"error": "no_master_agent"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "invalid_body"}, status_code=400)

    model = body.get("model")
    if model is not None and not isinstance(model, str):
        return JSONResponse({"error": "invalid_model"}, status_code=422)
    model = (model or "").strip() or None

    # Gesetztes Modell gegen den Katalog validieren (keine beliebigen Strings).
    if model is not None:
        entries = await registry.list_models("chat")
        valid = {e.id for e in entries}
        if model not in valid:
            return JSONResponse({"error": "unknown_model"}, status_code=422)

    sid = _voice_session_id(master["id"])
    if not sid:
        return JSONResponse({"error": "no_voice_session"}, status_code=409)

    sessions_db.set_model_override(sid, model)
    return {"override": model, "agent_default": master.get("llm_model") or "", "has_session": True}


@router.get("/llm/models")
async def list_models(auth: tuple = Depends(require_auth)):
    """Modell-Katalog fürs Dropdown (chat-fähige Modelle) + Agent-Default."""
    username, _role = auth
    master = _find_master(username)
    agent_default = (master.get("llm_model") if master else "") or ""
    entries = await registry.list_models("chat")
    return {
        "agent_default": agent_default,
        "models": [
            {"id": e.id, "label": e.label, "provider": e.provider}
            for e in entries
        ],
    }
