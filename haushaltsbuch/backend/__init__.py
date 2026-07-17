"""Haushaltsbuch-Modul Backend — Platzhalter (Dummy).

V0.1 stellt nur den authentifizierten Statusvertrag bereit. Persistenz,
Bankimporte sowie Lidl-Plus- und PAYBACK-Anbindungen folgen separat.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

router = APIRouter()

_FEATURES = ("bookings_budgets", "bank_import", "lidl_plus", "payback")


@router.get("/status")
def status(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Meldet den Dummy-Zustand und die geplanten Funktionsbereiche."""
    return {
        "module": "haushaltsbuch",
        "state": "dummy",
        "features": {name: "planned" for name in _FEATURES},
    }


def register(ctx) -> None:
    ctx.register_router(router)
