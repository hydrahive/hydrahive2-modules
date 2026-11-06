"""Schnittstellen der Vorschau (preview_auth.py, preview_site.py). `router` mit HydraHive-Login (nur Admins),
`device_router` über den Geräte-Weg des Kerns (ohne Login, Bremse je Client-Adresse) – dort prüft das Ticket bzw. Cookie."""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import idle, network, preview_auth, preview_net, preview_site, state

logger = logging.getLogger(__name__)
router = APIRouter()
device_router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


def device_open() -> None:
    """Geräte-Weg braucht eine Prüfung – hier nichts vorab: Ticket bzw. Cookie prüft die Route selbst."""


@router.post("/projects/{project_id}/preview/open")
async def preview_open(project_id: str, p: Admin, body: Empty, request: Request) -> dict:
    """Bereitet den Weg vor (Regel im Netz, nginx-Block – beides nur wenn nötig), weckt das Projekt, gibt den Link."""
    row = state.get_row(project_id)
    if row is None or row["owner"] != p.username:
        raise coded(status.HTTP_404_NOT_FOUND, "vibe_project_not_found")
    if row["state"] not in ("ready", "sleeping"):
        raise coded(status.HTTP_409_CONFLICT, "vibe_not_ready")
    try:
        await idle.wake(project_id)
        await preview_net.open_port()
    except (network.VibeNetworkError, RuntimeError) as exc:
        logger.warning("Vibe: Vorschau-Weg nicht vorbereitet: %s", getattr(exc, "code", exc))
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, getattr(exc, "code", "vibe_container_down")) from None
    if not preview_site.is_applied(data_dir=preview_site.data_dir()):
        ok = await asyncio.to_thread(preview_site.apply, root=preview_site.root, data_dir=preview_site.data_dir())
        if not ok:
            raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "vibe_preview_unavailable")
    ticket = preview_auth.new_ticket(p.user_id, project_id)
    url = preview_auth.preview_url(request.headers.get("host", ""), ticket)
    if url is None:
        preview_auth._tickets.pop(ticket, None)
        raise coded(status.HTTP_400_BAD_REQUEST, "vibe_preview_bad_host")
    return {"url": url}


@device_router.get("/preview/login")
def preview_login(t: Annotated[str, Query(min_length=1, max_length=128)]) -> Response:
    got = preview_auth.redeem(t)
    if got is None:
        raise coded(status.HTTP_401_UNAUTHORIZED, "vibe_preview_login_required")
    r = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    r.set_cookie(preview_auth.COOKIE, preview_auth.issue_cookie(*got), max_age=preview_auth.MAX_AGE, path="/",
                 httponly=True, secure=True, samesite="none")
    return r


@device_router.get("/preview/auth")
async def preview_check(hh_vibe_preview: Annotated[str | None, Cookie()] = None) -> Response:
    pid = preview_auth.project_from(hh_vibe_preview)
    target = await preview_net.address(pid) if pid else None
    if target is None:
        raise coded(status.HTTP_401_UNAUTHORIZED, "vibe_preview_login_required")
    state.touch(pid)                              # eine offene Vorschau hält den Container wach
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"X-Vibe-Up": target})
