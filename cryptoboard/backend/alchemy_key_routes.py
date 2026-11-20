"""Alchemy-Key-Routen — /api/modules/cryptoboard/alchemy-key.

Setzen (mit Vorab-Test VOR dem Speichern), Status (nur maskiert), Löschen.
Login-pflichtig, strikt user-scoped. Der Key selbst verlässt diesen Endpunkt
NIE im Klartext — weder im Erfolgs- noch im Fehlerfall.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import alchemy_key

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]

# Fehlercode → HTTP-Status. Alles andere (unbekannter Code) → 400.
_STATUS_BY_CODE = {
    "alchemy_key_empty": status.HTTP_400_BAD_REQUEST,
    "alchemy_key_invalid": status.HTTP_401_UNAUTHORIZED,
    "alchemy_base_not_enabled": status.HTTP_403_FORBIDDEN,
    "alchemy_network_error": status.HTTP_502_BAD_GATEWAY,
    "alchemy_test_failed": status.HTTP_502_BAD_GATEWAY,
    "cryptoboard_onchain_disabled": status.HTTP_503_SERVICE_UNAVAILABLE,
}


class KeyIn(BaseModel):
    key: str = Field(min_length=1, max_length=200)


@router.put("/alchemy-key")
@router.post("/alchemy-key")
async def set_key(body: KeyIn, auth: Auth) -> dict:
    user, _ = auth
    ok, code = await alchemy_key.set_key(user, body.key)
    if not ok:
        raise coded(_STATUS_BY_CODE.get(code, status.HTTP_400_BAD_REQUEST), code)
    return alchemy_key.status(user)


@router.get("/alchemy-key")
def get_status(auth: Auth) -> dict:
    user, _ = auth
    return alchemy_key.status(user)


@router.delete("/alchemy-key")
def remove_key(auth: Auth) -> dict:
    user, _ = auth
    alchemy_key.delete_key(user)
    return {"ok": True}
