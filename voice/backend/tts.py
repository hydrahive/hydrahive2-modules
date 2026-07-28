"""Voice-Modul E7 — Stimmenauswahl (TTS).

Liest/setzt die TTS-Config der Bridge (backend local/cloud, Cloud-Modell,
Cloud-Stimme) und liefert den Speech-Modell-Katalog fürs Dropdown.

Proxied an die Bridge-Control-API (127.0.0.1:8898) — die Bridge nutzt die
Config sofort beim nächsten Voice-Turn und persistiert sie.
"""
from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.llm import media_models

router = APIRouter()

BRIDGE_URL = os.environ.get("VOICE_BRIDGE_CONTROL_URL", "http://127.0.0.1:8898").rstrip("/")
_TIMEOUT = 4.0
_BACKENDS = ("local", "cloud")


@router.get("/tts")
async def get_tts(_auth: tuple = Depends(require_auth)):
    """Aktuelle TTS-Auswahl (von der Bridge). Bridge down → leer + bridge:down."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{BRIDGE_URL}/tts")
            r.raise_for_status()
            cfg = r.json()
    except Exception:
        return {"bridge": "down", "config": None}
    return {"bridge": "up", "config": cfg}


@router.put("/tts")
async def put_tts(request: Request, _auth: tuple = Depends(require_auth)):
    """Setzt TTS backend/model/voice. Validiert, dann an die Bridge."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "invalid_body"}, status_code=400)

    payload: dict = {}
    backend = body.get("backend")
    if backend is not None:
        if backend not in _BACKENDS:
            return JSONResponse({"error": "backend_invalid"}, status_code=422)
        payload["backend"] = backend

    voice = body.get("voice")
    if voice is not None:
        if not isinstance(voice, str):
            return JSONResponse({"error": "voice_invalid"}, status_code=422)
        payload["voice"] = voice

    model = body.get("model")
    if model is not None:
        if not isinstance(model, str):
            return JSONResponse({"error": "model_invalid"}, status_code=422)
        # Nicht-leeres Modell gegen den Speech-Katalog prüfen.
        if model:
            models = await media_models.list_speech_models()
            valid = {m["id"] if isinstance(m, dict) else m for m in models}
            if model not in valid:
                return JSONResponse({"error": "unknown_model"}, status_code=422)
        payload["model"] = model

    if not payload:
        return JSONResponse({"error": "no_valid_fields"}, status_code=422)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(f"{BRIDGE_URL}/tts", json=payload)
    except Exception:
        return JSONResponse({"error": "bridge_unreachable"}, status_code=503)
    if r.status_code >= 400:
        try:
            detail = r.json()
        except Exception:
            detail = {"error": "bridge_error"}
        return JSONResponse(detail, status_code=r.status_code)
    return {"bridge": "up", "config": r.json()}


@router.get("/tts/models")
async def tts_models(_auth: tuple = Depends(require_auth)):
    """Speech-Modell-Katalog (jedes Modell bringt seine Stimmen mit) + Default."""
    models = await media_models.list_speech_models()
    out = []
    for m in models:
        if isinstance(m, dict):
            out.append({"id": m.get("id"), "voices": list(m.get("voices") or [])})
        else:
            out.append({"id": m, "voices": []})
    try:
        default = media_models.get_media_model("tts")
    except Exception:
        default = ""
    return {"default": default, "models": out}
