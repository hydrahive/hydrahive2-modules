"""Routen „Sender“ (PLAN-E2.md Punkt 6, „Rechte“): sehen alle mit module.radiostream, steuern nur radiostream.control.

Der Status nennt keine Passwörter, keine Pfade und keine Adressen von Hörern. Speichern bei laufendem Sender wendet die
Einstellungen sofort an (Konfiguration + Hörer-Seite neu, Sender startet kurz neu).
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from hydrahive.access import check
from hydrahive.access.deps import require_capability
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import control, rotation, station

CONTROL = "radiostream.control"
router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]
Controller = Annotated[AuthPrincipal, Depends(require_capability(CONTROL))]
_HTTP = {"radiostream_service_missing": status.HTTP_409_CONFLICT, "radiostream_not_running": status.HTTP_409_CONFLICT,
         "radiostream_port_in_use": status.HTTP_409_CONFLICT}


class StationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=200)
    subtitle: str | None = Field(default=None, max_length=200)
    artist_gap_min: int | None = None
    title_gap_days: int | None = None
    listen_port: int | None = None
    reach: Literal["all", "home", "off"] | str | None = None
    max_listeners: int | None = None


def _can_control(p: AuthPrincipal) -> bool:
    return check.can_use(user_id=p.user_id, role=p.role, capability=CONTROL)


def _view(p: AuthPrincipal) -> dict:
    st = control.status()
    return {"installed": st["installed"], "running": st["running"], "now": control.now_playing(),
            "listeners": control.listeners() if st["running"] else 0, "recent": rotation.recent(10),
            "settings": station.get(), "can_control": _can_control(p)}


def _do(action) -> None:
    try:
        action()
    except control.ControlError as exc:
        raise coded(_HTTP.get(exc.code, status.HTTP_502_BAD_GATEWAY), exc.code) from None


@router.get("/station")
def get_station(p: Principal):
    return _view(p)


@router.post("/station/start")
def start_station(p: Controller):
    _do(control.start)
    return _view(p)


@router.post("/station/stop")
def stop_station(p: Controller):
    _do(control.stop)
    return _view(p)


@router.post("/station/skip")
def skip_title(p: Controller):
    _do(control.skip)
    return _view(p)


@router.put("/station/settings")
def save_station(body: StationIn, p: Controller):
    try:
        station.save(user=p.username, **body.model_dump(exclude_none=True))
    except station.StationError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None
    if control.status()["running"]:
        _do(control.start)
    return _view(p)
