from __future__ import annotations

from fastapi import APIRouter, Query, status

from hydrahive.api.middleware.errors import coded

from . import lidl_auth, loyalty_connections, loyalty_receipts, loyalty_sync
from .access import Principal
from .lidl_config import enabled as lidl_enabled
from .loyalty_requests import (
    LidlAuthComplete, LidlAuthStart, LoyaltyConnectionCreate, LoyaltyConnectionUpdate,
)

router = APIRouter(prefix="/loyalty")


@router.get("/provider-status")
def provider_status(principal: Principal) -> dict:
    del principal
    return {
        "lidl_plus": {"enabled": lidl_enabled(), "experimental": True},
        "payback": {"enabled": False, "experimental": True},
    }


@router.post("/lidl/auth/start")
def start_lidl_auth(body: LidlAuthStart, principal: Principal) -> dict:
    try:
        return lidl_auth.start_auth(body, principal)
    except lidl_auth.AuthFlowError as exc:
        raise coded(exc.status_code, exc.code) from exc


@router.post("/lidl/auth/complete")
async def complete_lidl_auth(body: LidlAuthComplete, principal: Principal) -> dict:
    try:
        return await lidl_auth.complete_auth(body, principal)
    except lidl_auth.AuthFlowError as exc:
        raise coded(exc.status_code, exc.code) from exc


@router.get("/receipts")
def list_receipts(principal: Principal) -> list[dict]:
    return loyalty_receipts.list_receipts(principal)


@router.get("/receipts/{receipt_id}")
def receipt_detail(receipt_id: int, principal: Principal) -> dict:
    return loyalty_receipts.receipt_detail(receipt_id, principal)


@router.get("/connections")
def list_connections(principal: Principal) -> list[dict]:
    return loyalty_connections.list_connections(principal)


@router.post("/connections", status_code=status.HTTP_201_CREATED)
def create_connection(body: LoyaltyConnectionCreate, principal: Principal) -> dict:
    return loyalty_connections.create_connection(body, principal)


@router.post("/connections/{connection_id}/sync")
async def sync_connection(connection_id: int, principal: Principal) -> dict:
    return await loyalty_sync.sync_connection(connection_id, principal)


@router.get("/connections/{connection_id}/sync-runs")
def list_sync_runs(connection_id: int, principal: Principal) -> list[dict]:
    return loyalty_sync.list_sync_runs(connection_id, principal)


@router.put("/connections/{connection_id}")
def update_connection(
    connection_id: int, body: LoyaltyConnectionUpdate, principal: Principal
) -> dict:
    return loyalty_connections.update_connection(connection_id, body, principal)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: int, principal: Principal, revision: int = Query(ge=1)
) -> None:
    loyalty_connections.delete_connection(connection_id, revision, principal)
