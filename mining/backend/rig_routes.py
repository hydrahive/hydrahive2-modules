"""Rig-Verwaltung für Admins (unter /api/modules/mining, zusätzlich mining.control).

GET    /rigs                 Liste (ohne Tokens)
POST   /rigs/pairing         Kopplungs-Code + fertiger Installationsbefehl
POST   /rigs/{id}/approve    freigeben
POST   /rigs/{id}/revoke     sperren (Token sofort ungültig)
POST   /rigs/{id}/enabled    an/aus  {"enabled": bool}
DELETE /rigs/{id}            gesperrten Rig löschen
"""
from __future__ import annotations

import shlex
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from . import pairing, rigs, tls_pin
from .access import Control

rig_router = APIRouter(prefix="/rigs")
CLIENT_URL = "https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/install.sh"


def _not_found(ok: bool) -> None:
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "rig_not_found_or_wrong_state"})


@rig_router.get("")
def list_rigs(_control: Control) -> list[dict]:
    return rigs.list_rigs()


@rig_router.post("/pairing")
def create_pairing(request: Request, _control: Control, body: dict[str, Any]) -> dict:
    try:
        created = pairing.create(str(body.get("name") or ""), created_by=None)
    except pairing.PairingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": str(exc)}) from exc
    host = request.headers.get("host") or request.url.netloc
    server = f"https://{host}"
    pin = tls_pin.server_pin(host)
    args = ["--server", server, "--code", created["code"]] + (["--pin", pin] if pin else [])
    cmd = f"curl -fsSL {CLIENT_URL} | sudo sh -s -- {shlex.join(args)}"
    return {**created, "server": server, "pin": pin, "command": cmd}


@rig_router.post("/{rig_id}/approve")
def approve(_control: Control, rig_id: str) -> dict:
    _not_found(rigs.approve(rig_id))
    return {"ok": True}


@rig_router.post("/{rig_id}/revoke")
def revoke(_control: Control, rig_id: str) -> dict:
    _not_found(rigs.revoke(rig_id))
    return {"ok": True}


@rig_router.post("/{rig_id}/enabled")
def set_enabled(_control: Control, rig_id: str, body: dict[str, Any]) -> dict:
    if not isinstance(body.get("enabled"), bool):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "enabled_must_be_bool"})
    _not_found(rigs.set_enabled(rig_id, body["enabled"]))
    return {"ok": True}


@rig_router.delete("/{rig_id}")
def delete(_control: Control, rig_id: str) -> dict:
    _not_found(rigs.delete(rig_id))
    return {"ok": True}
