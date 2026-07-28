"""Voice-Modul Backend — Voicebox für den HydraHive-Sprachassistenten.

register(ctx) mountet den Router unter /api/modules/voice/...

E2: echter Bridge-/Geräte-Status + Geräte-Einstellungen (Lautstärke, Mute,
Wake-Sound, Wake-Word-Empfindlichkeit, LED-Ring). Das Backend spricht nicht
direkt mit dem Gerät, sondern proxied an die lokale Control-API der Bridge
(voice-pe/bridge/control.py) — so bleibt die Bridge der einzige ESPHome-Client.
"""
from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi import Request
from fastapi.responses import JSONResponse

from hydrahive.api.middleware.auth import require_auth

router = APIRouter()

# Lokale Control-API der Bridge (nur 127.0.0.1). Überschreibbar per ENV.
BRIDGE_URL = os.environ.get("VOICE_BRIDGE_CONTROL_URL", "http://127.0.0.1:8898").rstrip("/")
_TIMEOUT = 4.0

# Felder die das Modul-Backend als Einstellungen durchreicht.
_SETTING_FIELDS = (
    "volume",
    "mute",
    "wake_sound",
    "wake_word_sensitivity",
    "led_on",
    "led_brightness",
)
_VALID_SENSITIVITIES = (
    "Slightly sensitive",
    "Moderately sensitive",
    "Very sensitive",
)


async def _bridge_get(path: str) -> dict | None:
    """GET gegen die Bridge-Control-API. None wenn Bridge nicht erreichbar."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(f"{BRIDGE_URL}{path}")
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


@router.get("/status")
async def voice_status(_user: dict = Depends(require_auth)) -> dict:
    """Grundstatus der Voicebox — echter Bridge-/Geräte-Zustand (E2)."""
    health = await _bridge_get("/health")
    if health is None:
        return {
            "module": "voice",
            "stage": "e2",
            "bridge": "down",
            "device": "disconnected",
        }
    return {
        "module": "voice",
        "stage": "e2",
        "bridge": "up",
        "device": "connected" if health.get("connected") else "disconnected",
    }


@router.get("/settings")
async def get_settings(_user: dict = Depends(require_auth)):
    """Liefert die aktuellen Geräte-Einstellungen (Live-Werte von der Bridge)."""
    state = await _bridge_get("/state")
    if state is None:
        return JSONResponse(
            {"bridge": "down", "settings": None},
            status_code=200,
        )
    settings = {k: state.get(k) for k in _SETTING_FIELDS}
    return {
        "bridge": "up",
        "device": "connected" if state.get("connected") else "disconnected",
        "settings": settings,
    }


@router.put("/settings")
async def put_settings(request: Request, _user: dict = Depends(require_auth)):
    """Setzt Geräte-Einstellungen — validiert und an die Bridge weitergereicht."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "invalid_body"}, status_code=400)

    # Nur bekannte Felder durchreichen + grob validieren (die Bridge validiert
    # nochmal streng, aber wir wollen früh 422 ohne Geräte-Call).
    payload: dict = {}
    if "volume" in body and body["volume"] is not None:
        v = body["volume"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
            return JSONResponse({"error": "volume_invalid"}, status_code=422)
        payload["volume"] = float(v)
    if "led_brightness" in body and body["led_brightness"] is not None:
        b = body["led_brightness"]
        if isinstance(b, bool) or not isinstance(b, (int, float)) or not (0.0 <= float(b) <= 1.0):
            return JSONResponse({"error": "led_brightness_invalid"}, status_code=422)
        payload["led_brightness"] = float(b)
    for key in ("mute", "wake_sound", "led_on"):
        if key in body and body[key] is not None:
            if not isinstance(body[key], bool):
                return JSONResponse({"error": f"{key}_invalid"}, status_code=422)
            payload[key] = body[key]
    if "wake_word_sensitivity" in body and body["wake_word_sensitivity"] is not None:
        s = body["wake_word_sensitivity"]
        if s not in _VALID_SENSITIVITIES:
            return JSONResponse({"error": "wake_word_sensitivity_invalid"}, status_code=422)
        payload["wake_word_sensitivity"] = s

    if not payload:
        return JSONResponse({"error": "no_valid_fields"}, status_code=422)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(f"{BRIDGE_URL}/set", json=payload)
    except Exception:
        return JSONResponse({"error": "bridge_unreachable"}, status_code=503)

    if r.status_code == 503:
        return JSONResponse({"error": "device_disconnected"}, status_code=503)
    if r.status_code >= 400:
        try:
            detail = r.json()
        except Exception:
            detail = {"error": "bridge_error"}
        return JSONResponse(detail, status_code=r.status_code)

    state = r.json()
    return {
        "bridge": "up",
        "device": "connected" if state.get("connected") else "disconnected",
        "settings": {k: state.get(k) for k in _SETTING_FIELDS},
    }


@router.get("/transcript")
async def get_transcript(
    since: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(require_auth),
):
    """Voice-Verlauf (letzte Turns) — proxied von der Bridge. E3.

    Liefert nur Turns mit id > `since` (inkrementelles Polling). Bridge nicht
    erreichbar → leere, saubere Antwort (kein 500)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(
                f"{BRIDGE_URL}/transcript",
                params={"since": since, "limit": limit},
            )
            r.raise_for_status()
            data = r.json()
    except Exception:
        return {"bridge": "down", "turns": [], "cursor": since}
    return {
        "bridge": "up",
        "turns": data.get("turns", []),
        "cursor": data.get("cursor", since),
    }


def register(ctx) -> None:
    ctx.register_router(router)
