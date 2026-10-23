"""Routen der Microsoft-Anmeldung (PLAN-M1b) unter /api/modules/mailbox/… (Kern-Tor davor: Login + module.mailbox).

- /microsoft/app, /microsoft/app/check   nur Admin: Client-ID der HydraHive-App bei Microsoft (einmal global)
- /microsoft/status                      alle: ist die Anmeldung eingerichtet? (ohne Client-ID)
- /microsoft/flows, /microsoft/flows/{id} Anmeldung starten / Stand abfragen (nur eigene Vorgänge, sonst 404)
- /microsoft/accounts                    Konto aus fertiger Anmeldung anlegen
- /accounts/{id}/microsoft               bestehendes Konto neu anmelden
Keine Antwort enthält device_code, Zugriffs- oder Refresh-Token.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import accounts, ms_accounts, ms_app, ms_flows, oauth_ms

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Admin = Annotated[tuple[str, str], Depends(require_admin)]
FlowId = Field(min_length=10, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class AppIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(default="", max_length=64)
    tenant: str = Field(default="common", max_length=253)


class MsAccountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flow_id: str = FlowId
    address: str = Field(min_length=3, max_length=254)
    label: str = Field(default="", max_length=200)


class ReauthIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flow_id: str = FlowId


@router.get("/microsoft/app")
def get_app(admin: Admin) -> dict:
    return ms_app.get()


@router.put("/microsoft/app")
def put_app(body: AppIn, admin: Admin) -> dict:
    try:
        return ms_app.save(body.client_id, body.tenant)
    except ValueError as e:
        raise coded(422, "invalid", message=str(e)) from None


@router.post("/microsoft/app/check")
async def check_app(admin: Admin) -> dict:
    """Fragt einen Geräte-Code an: klappt das, ist die App richtig eingerichtet (der Code wird nicht benutzt)."""
    app = ms_app.get()
    if not app["client_id"]:
        return {"ok": False, "error": "not_configured", "message": "Keine Client-ID eingetragen"}
    try:
        await asyncio.to_thread(oauth_ms.device_code, app["client_id"], app["tenant"])
    except oauth_ms.OAuthError as e:
        return {"ok": False, "error": e.code, "message": e.description}
    return {"ok": True}


@router.get("/microsoft/status")
def ms_status(auth: Auth) -> dict:
    return {"configured": ms_app.configured()}


@router.post("/microsoft/flows", status_code=status.HTTP_201_CREATED)
async def start_flow(auth: Auth) -> dict:
    try:
        return await asyncio.to_thread(ms_flows.start, auth[0])
    except ms_flows.NotConfigured:
        raise coded(status.HTTP_409_CONFLICT, "microsoft_not_configured") from None
    except ms_flows.TooMany:
        raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_flows") from None
    except oauth_ms.OAuthError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, "microsoft", error=e.code, message=e.description) from None


@router.get("/microsoft/flows/{flow_id}")
async def flow_status(flow_id: str, auth: Auth) -> dict:
    st = await asyncio.to_thread(ms_flows.status, auth[0], flow_id)
    if st is None:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return st


def _fail(e: Exception):
    if isinstance(e, ms_flows.FlowError):
        if str(e) == "not_done":
            raise coded(status.HTTP_409_CONFLICT, "flow_not_done") from None
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    if isinstance(e, accounts.NotFound):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    if isinstance(e, accounts.Conflict):
        raise coded(status.HTTP_409_CONFLICT, "exists") from None
    if isinstance(e, accounts.ConnectError):
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, message=str(e)) from None
    if isinstance(e, ValueError):
        raise coded(422, "invalid", message=str(e)) from None
    raise e


@router.post("/microsoft/accounts", status_code=status.HTTP_201_CREATED)
async def create_ms_account(body: MsAccountIn, auth: Auth) -> dict:
    try:
        a = await asyncio.to_thread(ms_accounts.create, auth[0], body.flow_id, body.address, body.label)
    except Exception as e:  # noqa: BLE001 - _fail ordnet zu, Unbekanntes wird neu geworfen
        _fail(e)
    from . import sync_job
    asyncio.create_task(sync_job.sync_now(auth[0], a["id"]))   # sofort abgleichen wie bei Passwort-Konten
    return a


@router.post("/accounts/{aid}/microsoft")
async def reauth(aid: str, body: ReauthIn, auth: Auth) -> dict:
    try:
        return await asyncio.to_thread(ms_accounts.reauth, auth[0], aid, body.flow_id)
    except Exception as e:  # noqa: BLE001
        _fail(e)
