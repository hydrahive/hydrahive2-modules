"""Geräte-Routen für Rigs (Kern: /api/module-device/mining, ohne Nutzer-Login).

POST /enroll   Code → Token        (auth: gültiger, unbenutzter Kopplungs-Code)
POST /report   Zustand melden      (auth: Rig-Token)  → Antwort = Soll-Zustand

Der Kern hängt Rate-Limit + ``device_auth`` zwingend vor jede Route.
``device_auth`` lässt zwei Nachweise zu: ``Authorization: Bearer hhrig_…``
(Rig-Token) oder ``X-Pairing-Code`` (nur für /enroll sinnvoll). Die Routen
prüfen danach selbst, ob der passende Nachweis vorliegt.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from hydrahive.api.middleware.client_ip import client_ip

from . import pairing, rigs

device_router = APIRouter()
_UNAUTH = {"code": "device_unauthorized"}


class _Device:
    def __init__(self, rig: dict | None, code: str | None) -> None:
        self.rig, self.code = rig, code


def device_auth(
    authorization: str | None = Header(None),
    x_pairing_code: str | None = Header(None, max_length=32),
) -> _Device:
    if authorization and authorization.lower().startswith("bearer "):
        rig = rigs.by_token(authorization[7:].strip())
        if rig:
            return _Device(rig, None)
    elif x_pairing_code and pairing.peek(x_pairing_code):
        return _Device(None, x_pairing_code)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTH)


Device = Annotated[_Device, Depends(device_auth)]


@device_router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll(request: Request, body: dict[str, Any], dev: Device) -> dict:
    if not dev.code:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTH)
    try:
        return rigs.enroll(dev.code, body.get("info") or {}, client_ip(request))
    except rigs.RigError as exc:
        code = status.HTTP_409_CONFLICT if str(exc) == "rig_name_taken" else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(code, detail={"code": str(exc)}) from exc


@device_router.post("/report")
def report(request: Request, body: dict[str, Any], dev: Device) -> dict:
    if not dev.rig:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTH)
    try:
        rigs.report(dev.rig, body, client_ip(request))
    except rigs.RigError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail={"code": str(exc)}) from exc
    return {"rig": {"name": dev.rig["name"], "status": dev.rig["status"]}, "desired": rigs.desired(dev.rig)}
