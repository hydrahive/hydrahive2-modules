"""Alert-Routen — /api/modules/cryptoboard/alerts[...].

Eigenständige Preis-/Portfolio-Alerts (neben den Butler-Flows) plus die In-App-
Benachrichtigungs-Historie. Login-pflichtig, strikt user-scoped.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import alerts_store as store
from .validators import ID_RE

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class AlertIn(BaseModel):
    kind: str = Field(min_length=1, max_length=40)
    coin_id: str = Field(default="", max_length=80)
    symbol: str = Field(default="", max_length=20)
    threshold: float
    note: str = Field(default="", max_length=200)


class ActiveIn(BaseModel):
    active: bool


@router.get("/alerts")
def list_alerts(auth: Auth) -> list[dict]:
    user, _ = auth
    return store.list_for(user)


@router.post("/alerts")
def add_alert(body: AlertIn, auth: Auth) -> dict:
    user, _ = auth
    if body.kind not in store.KINDS:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_kind")
    coin_id = body.coin_id.strip().lower()
    if not store.is_portfolio(body.kind):
        if not ID_RE.match(coin_id):
            raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    else:
        coin_id = ""
    try:
        alert_id = store.add(
            user, kind=body.kind, coin_id=coin_id,
            symbol=body.symbol.strip().upper(), threshold=body.threshold,
            note=body.note.strip(),
        )
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"ok": True, "id": alert_id}


@router.patch("/alerts/{alert_id}")
def toggle_alert(alert_id: int, body: ActiveIn, auth: Auth) -> dict:
    user, _ = auth
    if not store.set_active(user, alert_id, body.active):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return {"ok": True}


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, auth: Auth) -> dict:
    user, _ = auth
    if not store.remove(user, alert_id):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return {"ok": True}


# ------------------------------------------------------------------ Events
@router.get("/alerts/events")
def list_events(auth: Auth, limit: int = 50) -> dict:
    user, _ = auth
    return {"events": store.list_events(user, limit), "unseen": store.unseen_count(user)}


@router.post("/alerts/events/seen")
def mark_events_seen(auth: Auth) -> dict:
    user, _ = auth
    store.mark_seen(user)
    return {"ok": True}
