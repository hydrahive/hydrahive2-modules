"""Ansicht ohne Login (Spec §4, §4a): /api/module-device/diagramme/sandbox/{id}?exp&sig.

Der Kern hängt `device_auth` vor jede Route und setzt ein Rate-Limit. nginx setzt an dieser Stelle fest die
Sandbox-CSP (Kern-Spec module-view-sandbox); wir setzen sie zusätzlich selbst (direkter Zugriff auf den Port, Mac).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from . import links, store

SANDBOX_CSP = ("sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none'; "
               "script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; "
               "connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'")
HEADERS = {"Content-Security-Policy": SANDBOX_CSP, "X-Content-Type-Options": "nosniff",
           "Referrer-Policy": "no-referrer", "Cache-Control": "no-store", "X-Frame-Options": "SAMEORIGIN"}

device_router = APIRouter()


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "diagram_not_found"})


def device_auth(request: Request, exp: str | None = Query(None, max_length=20),
                sig: str | None = Query(None, max_length=128)) -> None:
    """Nur die Sandbox-Ansicht mit gültiger Signatur. Alles andere: 404 ohne Hinweis."""
    view_id = request.path_params.get("view_id")
    if not (view_id and exp and sig and exp.isdigit() and links.check(view_id, int(exp), sig)):
        raise _not_found()


@device_router.get("/sandbox/{view_id}", response_class=HTMLResponse)
def sandbox(view_id: str) -> HTMLResponse:
    page = store.html(view_id)
    if page is None:
        raise _not_found()
    return HTMLResponse(page, headers=HEADERS)
