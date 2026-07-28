"""Voice-Modul E6 — STT/Transcript-Modell anzeigen.

Liest via Wyoming-`describe` das aktive Whisper-Modell des STT-Service
(faster-whisper auf 127.0.0.1:10300). Read-only: das Modell WECHSELN geht nicht
über das Cockpit (Modell = --model-Startparameter des Service, Wechsel = Neustart
mit root). Deshalb hier nur Anzeige + Hinweis im Frontend.

Nutzt die Wyoming-Framing-Helfer aus dem Core statt eigener Parserei.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

router = APIRouter()

STT_HOST = "127.0.0.1"
STT_PORT = 10300
_CONNECT_TIMEOUT = 2.0
_READ_TIMEOUT = 2.0


async def read_stt_info() -> dict:
    """Fragt den STT-Service via Wyoming describe nach seinem aktiven Modell.

    Gibt {available, program, model, languages} zurück. Bei jedem Fehler
    (nicht erreichbar, Timeout) → available=False, statt zu werfen.
    """
    from hydrahive.voice._wyoming import recv_event, send_event

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(STT_HOST, STT_PORT), timeout=_CONNECT_TIMEOUT
        )
    except Exception:
        return {"available": False, "program": None, "model": None, "languages": []}

    try:
        await send_event(writer, "describe")
        # Auf das info-Event warten (max. wenige Events durchlassen).
        for _ in range(5):
            etype, data, _payload = await asyncio.wait_for(
                recv_event(reader), timeout=_READ_TIMEOUT
            )
            if etype == "info":
                return _parse_info(data)
        return {"available": False, "program": None, "model": None, "languages": []}
    except Exception:
        return {"available": False, "program": None, "model": None, "languages": []}
    finally:
        try:
            writer.close()
        except Exception:
            pass


def _parse_info(data: dict) -> dict:
    """Extrahiert program + aktives Modell aus dem Wyoming-info-Event."""
    asr = data.get("asr") or []
    for program in asr:
        models = program.get("models") or []
        # Bevorzugt ein installiertes Modell, sonst das erste.
        chosen = next((m for m in models if m.get("installed")), models[0] if models else None)
        if chosen:
            return {
                "available": True,
                "program": program.get("name"),
                "model": chosen.get("name"),
                "languages": list(chosen.get("languages") or [])[:8],
            }
    return {"available": False, "program": None, "model": None, "languages": []}


@router.get("/stt")
async def get_stt(_auth: tuple = Depends(require_auth)) -> dict:
    """Aktives STT/Whisper-Modell (read-only). Wechsel erfolgt am Service (root)."""
    return await read_stt_info()
