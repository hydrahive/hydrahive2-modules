from __future__ import annotations

from fastapi import APIRouter, Query, status

from . import loyalty_connections, loyalty_sync
from .access import Principal
from .loyalty_requests import LoyaltyConnectionCreate, LoyaltyConnectionUpdate

router = APIRouter(prefix="/loyalty")


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
