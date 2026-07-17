from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status

from . import ledger
from .access import Principal
from .models import RevisionIn, TransactionCreate, TransactionMetadataUpdate

router = APIRouter()


@router.get("/transactions")
def list_transactions(
    principal: Principal,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    query: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return ledger.list_transactions(
        principal, date_from, date_to, account_id, category_id, query, limit, offset
    )


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(body: TransactionCreate, principal: Principal) -> dict:
    return ledger.create_transaction(body, principal)


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: int, principal: Principal) -> dict:
    return ledger.get_transaction(transaction_id, principal)


@router.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: int, body: TransactionMetadataUpdate, principal: Principal
) -> dict:
    return ledger.update_metadata(transaction_id, body, principal)


@router.post("/transactions/{transaction_id}/reverse")
def reverse_transaction(
    transaction_id: int, body: RevisionIn, principal: Principal
) -> dict:
    return ledger.reverse_transaction(transaction_id, body.revision, principal)
