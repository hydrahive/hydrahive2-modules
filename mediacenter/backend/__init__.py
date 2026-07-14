"""Mediacenter-Modul Backend — Platzhalter (Dummy).

Aktuell ohne eigene Datenhaltung: register(ctx) hängt nur einen Router mit
einem Status-Endpoint ein (/api/modules/mediacenter/status). Die Anbindung
von Radarr, Sonarr, SABnzbd und der Usenet-Indexer-Suche folgt später.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

router = APIRouter()

# Geplante Dienste — vorerst nur als Statuswert "planned" gemeldet.
_SERVICES = ("radarr", "sonarr", "sabnzbd", "indexer")


@router.get("/status")
def status(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Meldet den Platzhalter-Status des Moduls und die geplanten Dienste."""
    return {
        "module": "mediacenter",
        "state": "dummy",
        "services": {name: "planned" for name in _SERVICES},
    }


def register(ctx) -> None:
    ctx.register_router(router)
