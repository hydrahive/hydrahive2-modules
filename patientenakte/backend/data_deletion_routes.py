"""HTTP-Schnittstelle zum Löschen eigener Gesundheitsdaten.

Spec: patientenakte/SPEC-daten-loeschen.md. Gelöscht wird immer nur für den
eingeloggten User. Eine user_id im Request wird ignoriert.

Auth über require_principal (nicht require_auth): Das prüft den Token gegen
den aktuellen User-Bestand. Ein alter Token eines gelöschten und unter
gleichem Namen neu angelegten Users kann so die Daten des neuen Users nicht
löschen. Die Gesundheitsdaten sind weiterhin per Username gespeichert.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

from . import data_deletion

router = APIRouter(prefix="/data-deletion", tags=["akte-data-deletion"])
Principal = Annotated[AuthPrincipal, Depends(require_principal)]
CONFIRM_WORD = "LÖSCHEN"


class DeletionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    scope: Literal["apple_health", "fhir", "ega", "all"]
    confirm: str | None = None
    date_from: str | None = Field(default=None, alias="from")
    date_to: str | None = Field(default=None, alias="to")


@router.get("/overview")
async def deletion_overview(principal: Principal) -> dict:
    return await run_in_threadpool(data_deletion.overview, principal.username)


@router.post("")
async def delete_own_data(body: DeletionRequest, principal: Principal) -> dict:
    if body.confirm != CONFIRM_WORD:
        raise HTTPException(400, "confirmation_required")
    try:
        # Im Threadpool: Apple Health kann bei GB-großen Rohdaten Minuten dauern
        # und darf den Event-Loop nicht blockieren.
        return await run_in_threadpool(
            data_deletion.delete_scope, principal.username, body.scope, body.date_from, body.date_to,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
