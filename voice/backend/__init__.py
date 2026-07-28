"""Voice-Modul Backend — Voicebox für den HydraHive-Sprachassistenten.

register(ctx) mountet den Router unter /api/modules/voice/...

Etappe 1 (E1): nur ein Status-Endpoint als Fundament. Die eigentliche
Geräte-/Bridge-Steuerung kommt in E2/E3.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

router = APIRouter()


@router.get("/status")
def voice_status(_user: dict = Depends(require_auth)) -> dict:
    """Grundstatus der Voicebox (E1: statisch, wird in E2 mit echten
    Bridge-/Geräte-Daten gefüllt)."""
    return {
        "module": "voice",
        "stage": "e1",
        "bridge": "unknown",
        "device": "unknown",
    }


def register(ctx) -> None:
    ctx.register_router(router)
