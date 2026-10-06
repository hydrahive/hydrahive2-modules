"""Storyteller — KI-gestütztes Schreiben von Büchern (Spec: storyteller/docs/specs, lokal).

Stufe 1, klickbarer ENTWURF: Die Oberfläche speichert Bücher noch im Browser, die
KI-Vorschläge sind Platzhalter. Das Backend meldet nur den Stand; die Ablage im
Projekt-Workspace (Spec §8/§9) kommt nach Tills Durchsicht des Entwurfs.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import require_auth

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]

STAGE = "draft"


@router.get("/status")
def status(_: Auth) -> dict:
    return {"stage": STAGE, "storage": "browser", "ai": "placeholder"}


def register(ctx) -> None:
    ctx.register_router(router)
