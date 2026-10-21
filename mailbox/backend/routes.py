"""Routen /api/modules/mailbox/… (PLAN-M1 Schritt 11). Das Kern-Tor davor prüft Login + module.mailbox.

Jede Route prüft hier zusätzlich den Besitz: fremde Konten/Mails sind 404 (nicht 403 – keine Existenz verraten).
Passwörter kommen nie in eine Antwort. Inhalte (HTML, Anhänge, .eml) in body_routes.py.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import access, accounts, providers, search, sync_job
from .body_routes import router as body_router
from .schemas import AccountIn, AccountPatch

router = APIRouter()
router.include_router(body_router)
# 422 als Zahl: die Konstante heißt je nach Starlette-Version anders (Kern erlaubt fastapi >= 0.111)
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _fail(e: Exception):
    if isinstance(e, accounts.NotFound):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    if isinstance(e, accounts.Conflict):
        raise coded(status.HTTP_409_CONFLICT, "exists") from None
    if isinstance(e, accounts.ConnectError):
        raise coded(status.HTTP_400_BAD_REQUEST, e.code, message=str(e)) from None
    if isinstance(e, ValueError):
        raise coded(422, "invalid", message=str(e)) from None
    raise e


@router.get("/suggest")
def suggest(auth: Auth, address: str = Query(max_length=254)) -> dict:
    try:
        return providers.suggest(address)
    except ValueError as e:
        _fail(e)


@router.get("/accounts")
def list_accounts(auth: Auth) -> list[dict]:
    return [{**a, "sync": sync_job.progress(a["id"])} for a in accounts.list_for(auth[0])]


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(body: AccountIn, auth: Auth, background: BackgroundTasks) -> dict:
    try:
        a = accounts.create(auth[0], body.model_dump())
    except Exception as e:  # noqa: BLE001 - _fail ordnet zu, Unbekanntes wird neu geworfen
        _fail(e)
    background.add_task(sync_job.sync_now, auth[0], a["id"])   # sofort abgleichen, nicht erst im 5-min-Takt
    return a


@router.get("/accounts/{aid}")
def get_account(aid: str, auth: Auth) -> dict:
    a = accounts.get_own(auth[0], aid)
    if not a:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return {**a, "sync": sync_job.progress(aid)}


@router.patch("/accounts/{aid}")
def patch_account(aid: str, body: dict, auth: Auth) -> dict:
    if "address" in body:
        raise coded(422, "invalid", message="Adresse nicht änderbar")
    try:
        data = AccountPatch.model_validate(body).model_dump(exclude_none=True)
        return accounts.update(auth[0], aid, data)
    except Exception as e:  # noqa: BLE001
        if e.__class__.__name__ == "ValidationError":
            raise coded(422, "invalid") from None
        _fail(e)


@router.delete("/accounts/{aid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(aid: str, auth: Auth) -> Response:
    try:
        accounts.remove(auth[0], aid)
    except accounts.NotFound as e:
        _fail(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/accounts/{aid}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_account(aid: str, auth: Auth) -> dict:
    if not accounts.get_own(auth[0], aid):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    started = await sync_job.sync_now(auth[0], aid)
    return {"started": started}


@router.get("/folders")
def folders(auth: Auth) -> list[dict]:
    return access.folders_for(auth[0])


@router.get("/messages")
def messages(auth: Auth, q: str = Query("", max_length=2000), folder_id: int | None = None,
             deleted: bool = False, inbox: bool = False, limit: int = Query(50, ge=1, le=200),
             offset: int = Query(0, ge=0)) -> dict:
    accs = access.accounts_map(auth[0])
    if folder_id is not None and not access.folder_owned(accs, folder_id):
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "fulltext": True}
    return search.search(accs, q, folder_id=folder_id, only_deleted=deleted, role="inbox" if inbox else None,
                         limit=limit, offset=offset)
