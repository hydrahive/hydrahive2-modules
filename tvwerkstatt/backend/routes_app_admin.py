"""Admin-Seite der HydraHive-App: /api/modules/tvwerkstatt/app/… (Login + Admin).

Code erzeugen (mit Server-Adresse und Zertifikats-Fingerabdruck für die App), Geräte auflisten, sperren, entfernen,
Testeinblendung schicken, letzte Ereignisse und Einblendungen eines Geräts.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, status
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import app_messages, app_pairing, app_tls
from .routes_look import Admin

router = APIRouter()
_STATUS = {"tvw_app_not_found": 404, "tvw_device_not_found": 404, "tvw_app_notice_not_found": 404,
           "tvw_app_name_taken": 409}


def _err(exc: app_pairing.AppError):
    return coded(_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST), exc.code)


class NewCode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    device_id: str = ""


class Notice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    body: str = ""
    buttons: list[str] = []


@router.get("/app/devices")
def list_devices(p: Admin) -> dict:
    from .routes_app_build import build_view
    return {"devices": app_pairing.all_devices(), **build_view()}


@router.post("/app/pairing", status_code=status.HTTP_201_CREATED)
def new_code(request: Request, body: NewCode, p: Admin) -> dict:
    try:
        out = app_pairing.create_code(body.name, body.device_id, p.username)
    except app_pairing.AppError as exc:
        raise _err(exc) from None
    host = request.headers.get("host", "")
    pin = app_tls.pin_for(host)
    return {**out, "server": f"https://{host}" if host else "", "pin": pin, "pin_short": app_tls.short(pin)}


@router.post("/app/devices/{app_id}/revoke")
def revoke(app_id: str, p: Admin) -> dict:
    try:
        app_pairing.revoke(app_id)
    except app_pairing.AppError as exc:
        raise _err(exc) from None
    return {"ok": True}


@router.delete("/app/devices/{app_id}")
def remove(app_id: str, p: Admin) -> dict:
    try:
        app_pairing.remove(app_id)
    except app_pairing.AppError as exc:
        raise _err(exc) from None
    return {"ok": True}


@router.post("/app/devices/{app_id}/notices", status_code=status.HTTP_201_CREATED)
def send_notice(app_id: str, body: Notice, p: Admin) -> dict:
    try:
        return {"notice_id": app_messages.send(app_id, body.title, body.body, body.buttons, p.username)}
    except app_pairing.AppError as exc:
        raise _err(exc) from None


@router.get("/app/devices/{app_id}/activity")
def activity(app_id: str, p: Admin) -> dict:
    if not any(d["app_id"] == app_id for d in app_pairing.all_devices()):
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_app_not_found")
    return {"events": app_messages.events(app_id), "notices": app_messages.notices(app_id)}
