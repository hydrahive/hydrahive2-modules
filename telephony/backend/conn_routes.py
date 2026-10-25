"""API der SIP-Verbindung (PLAN-EINSTELLUNGEN „API“). Fehler ohne Kennwort, Challenge oder Rohantwort."""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.inbound_ratelimit import check_rate

from . import connections
from .conn_models import ConnectionIn


class _NoEchoRoute(APIRoute):
    """Validierungsfehler ohne Eingabewerte zurückgeben (sonst stünde das Kennwort in der Antwort)."""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await original(request)
            except RequestValidationError as e:
                msgs = [str(err.get("msg", ""))[:160] for err in e.errors()][:5]
                fields = [".".join(str(p) for p in err.get("loc", ())[1:]) for err in e.errors()][:5]
                raise coded(422, "invalid", fields=fields, messages=msgs) from None

        return handler


router = APIRouter(route_class=_NoEchoRoute)
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _fail(e: Exception):
    if isinstance(e, connections.NotFound):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    if isinstance(e, connections.Invalid):
        code = 409 if e.code == "port_taken" else 422
        raise coded(code, e.code, message=str(e)) from None
    raise e


def _limit(auth: AuthPrincipal, action: str, limit: int) -> None:
    ok, retry = check_rate(f"telephony:{action}:{auth.user_id}", limit=limit, window=60)
    if not ok:
        raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", retry_after=retry)


@router.get("/connection")
def get_connection(auth: Auth) -> dict:
    return connections.public(auth.user_id)


@router.put("/connection")
def put_connection(body: ConnectionIn, auth: Auth) -> dict:
    _limit(auth, "save", 20)
    try:
        return connections.save(auth.user_id, body)
    except Exception as e:  # noqa: BLE001 - _fail ordnet zu, Unbekanntes wird neu geworfen
        _fail(e)


@router.post("/connection/connect")
async def connect(auth: Auth) -> dict:
    _limit(auth, "connect", 10)
    try:
        return await asyncio.to_thread(connections.connect, auth.user_id)
    except Exception as e:  # noqa: BLE001
        _fail(e)


@router.post("/connection/disconnect")
async def disconnect(auth: Auth) -> dict:
    try:
        return await asyncio.to_thread(connections.disconnect, auth.user_id)
    except Exception as e:  # noqa: BLE001
        _fail(e)


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(auth: Auth) -> Response:
    try:
        await asyncio.to_thread(connections.delete, auth.user_id)
    except Exception as e:  # noqa: BLE001
        _fail(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
