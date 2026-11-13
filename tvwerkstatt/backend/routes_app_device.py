"""Geräte-Routen der HydraHive-App: /api/module-device/tvwerkstatt/… – ohne Nutzer-Login.

Der Kern hängt Rate-Limit (240/min je IP) und `app_auth` zwingend vor jede Route. Zwei Nachweise: `Authorization:
Bearer hhtvw_…` (gekoppeltes Gerät) oder `X-Pairing-Code` (nur für /app/enroll). Jede Route prüft danach selbst, ob der
passende Nachweis vorliegt.

POST /app/enroll   Code → Schlüssel
POST /app/hello    Lebenszeichen + Zustand (an/aus, App vorne …), Antwort: Einstellungen für die App
POST /app/events   Ereignis melden
GET  /app/notices  Einblendungen abholen (lange Abfrage, ?after=&wait=)
POST /app/notices/{id}  gezeigt / Antwort
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from hydrahive.api.middleware.client_ip import client_ip

from . import app_messages, app_pairing

device_router = APIRouter()
_UNAUTH = {"code": "device_unauthorized"}


class _Dev:
    def __init__(self, app: dict | None, code: str | None) -> None:
        self.app, self.code = app, code


def app_auth(authorization: str | None = Header(None, max_length=200),
             x_pairing_code: str | None = Header(None, max_length=32)) -> _Dev:
    if authorization and authorization.lower().startswith("bearer "):
        app = app_pairing.by_token(authorization[7:].strip())
        if app:
            return _Dev(app, None)
    elif x_pairing_code and app_pairing.code_valid(x_pairing_code):
        return _Dev(None, x_pairing_code)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTH)


Dev = Annotated[_Dev, Depends(app_auth)]


def _app(dev: _Dev) -> dict:
    if not dev.app:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTH)
    return dev.app


def _bad(exc: app_pairing.AppError, code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
    return HTTPException(code, detail={"code": exc.code})


@device_router.post("/app/enroll", status_code=status.HTTP_201_CREATED)
def enroll(request: Request, body: dict[str, Any], dev: Dev) -> dict:
    if not dev.code:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTH)
    try:
        return app_pairing.enroll(dev.code, body.get("info") or {}, client_ip(request))
    except app_pairing.AppError as exc:
        raise _bad(exc, status.HTTP_409_CONFLICT if exc.code == "tvw_app_name_taken"
                   else status.HTTP_401_UNAUTHORIZED) from None


@device_router.post("/app/hello")
def hello(request: Request, body: dict[str, Any], dev: Dev) -> dict:
    app = _app(dev)
    state = body.get("state") if isinstance(body.get("state"), dict) else {}
    app_pairing.seen(app["app_id"], client_ip(request), state)
    return {"app": {"name": app["name"], "app_id": app["app_id"]}, "poll_seconds": 25}


@device_router.post("/app/events", status_code=status.HTTP_202_ACCEPTED)
def event(request: Request, body: dict[str, Any], dev: Dev) -> dict:
    app = _app(dev)
    try:
        app_messages.add_event(app["app_id"], str(body.get("kind") or ""), body.get("data") or {})
    except app_pairing.AppError as exc:
        raise _bad(exc) from None
    app_pairing.seen(app["app_id"], client_ip(request))
    return {"ok": True}


@device_router.get("/app/notices")
async def notices(request: Request, dev: Dev, after: int = 0, wait: float = 0) -> dict:
    app = _app(dev)
    app_pairing.seen(app["app_id"], client_ip(request))
    return {"notices": await app_messages.wait_pending(app["app_id"], after, wait)}


@device_router.post("/app/notices/{notice_id}")
def notice_done(notice_id: int, body: dict[str, Any], dev: Dev) -> dict:
    app = _app(dev)
    answer = body.get("answer")
    try:
        app_messages.mark(app["app_id"], notice_id, answer=None if answer is None else str(answer)[:20])
        if answer is not None:
            app_messages.add_event(app["app_id"], "answer", {"notice_id": notice_id, "answer": str(answer)[:20]})
    except app_pairing.AppError as exc:
        raise _bad(exc, status.HTTP_404_NOT_FOUND if exc.code == "tvw_app_notice_not_found"
                   else status.HTTP_400_BAD_REQUEST) from None
    return {"ok": True}
