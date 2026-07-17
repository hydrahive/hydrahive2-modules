"""Haushaltsbuch backend: shared ledger, planning and bank-import inbox."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

from .routes_household import router as household_router
from .routes_imports import router as import_router
from .routes_ledger import router as ledger_router
from .routes_planning import router as planning_router

router = APIRouter()


@router.get("/status")
def status(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return {
        "module": "haushaltsbuch",
        "state": "active",
        "features": {
            "bookings_budgets": "available",
            "bank_import": "available",
            "lidl_plus": "planned",
            "payback": "planned",
        },
    }


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(household_router)
    ctx.register_router(import_router)
    ctx.register_router(ledger_router)
    ctx.register_router(planning_router)
    ctx.register_migrations("migrations")
