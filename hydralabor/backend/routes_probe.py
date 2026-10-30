"""Schnittstellen der Probe-Anmeldung (probe_auth.py). `router` mit HydraHive-Login (nur Admins), `device_router`
ohne Login über den Geräte-Weg des Kerns (Bremse je Client-Adresse) – die Prüfung macht das Cookie bzw. Ticket."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import jobs, probe, probe_auth, probe_site, state

router = APIRouter()
device_router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


def device_open() -> None:
    """Geräte-Weg braucht eine Prüfung – hier nichts vorab: Ticket bzw. Cookie prüft die Route selbst."""


def _ready() -> None:
    if state.get()["step"] != "ready":
        raise coded(status.HTTP_409_CONFLICT, "labor_not_ready")


@router.get("/probe")
async def probe_state(p: Admin) -> dict:
    if state.get()["step"] != "ready":
        return {"built": False, "running": False, "user": "admin", "password": "", "port": probe_site.PORT,
                "open": False}
    return await probe.status()


@router.post("/probe/open")
def probe_open(p: Admin, body: Empty, request: Request) -> dict:
    _ready()
    ticket = probe_auth.new_ticket(p.user_id)
    url = probe_auth.probe_url(request.headers.get("host", ""), ticket)
    if url is None:
        probe_auth._tickets.pop(ticket, None)
        raise coded(status.HTTP_400_BAD_REQUEST, "labor_probe_bad_host")
    return {"url": url}


# Nach /probe/open: der Platzhalter würde „open“ sonst fangen (422).
@router.post("/probe/{action}", status_code=status.HTTP_202_ACCEPTED)
async def probe_job(p: Admin, action: Literal["build", "start", "stop"], body: Empty) -> dict:
    """async: jobs.start braucht die laufende Ereignisschleife (Befund L1)."""
    _ready()
    job = f"probe_{action}"
    if not jobs.start(job):
        raise coded(status.HTTP_409_CONFLICT, "labor_busy")
    return {"started": job}


@device_router.get("/probe/login")
def probe_login(t: Annotated[str, Query(min_length=1, max_length=128)]) -> Response:
    uid = probe_auth.redeem(t)
    if uid is None:
        raise coded(status.HTTP_401_UNAUTHORIZED, "labor_probe_login_required")
    r = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    r.set_cookie(probe_auth.COOKIE, probe_auth.issue_cookie(uid), max_age=probe_auth.MAX_AGE, path="/",
                 httponly=True, secure=True, samesite="strict")
    return r


@device_router.get("/probe/auth", status_code=status.HTTP_204_NO_CONTENT)
def probe_check(hh_labor_probe: Annotated[str | None, Cookie()] = None) -> Response:
    if not probe_auth.admin_from(hh_labor_probe):
        raise coded(status.HTTP_401_UNAUTHORIZED, "labor_probe_login_required")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
