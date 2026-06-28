"""Home-Assistant-Routen — /api/modules/homeassistant/*.

Alle Routen erfordern Login (require_auth). Sie proxien die HA-REST-API über den
client (URL+Token aus System-Settings) und stellen dem Frontend nur eingedampfte
Daten bereit — der HA-Token verlässt den Server nie. entity_id/domain/service
werden validiert, bevor sie in Upstream-URLs/Bodies fließen.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import client, favorites_store, validators

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


async def _guard(call):
    """HA-Aufruf ausführen und Config-/Upstream-Fehler in saubere HTTP-Codes mappen."""
    try:
        return await call()
    except client.HAConfigError as exc:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "ha_not_configured", message=str(exc))
    except client.HAError as exc:
        raise coded(status.HTTP_502_BAD_GATEWAY, "ha_upstream_error", message=str(exc))


@router.get("/test")
async def test(auth: Auth) -> dict:
    """Verbindungs-/Auth-Check für die Settings-/Dashboard-UI."""
    ping = await _guard(client.ping)
    cfg = await _guard(client.config)
    return {"ok": True, "message": ping.get("message"), "config": cfg}


@router.get("/states")
async def states(auth: Auth) -> list[dict]:
    return await _guard(client.states)


@router.get("/states/{entity_id}")
async def state(auth: Auth, entity_id: str) -> dict:
    if not validators.is_entity(entity_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_entity_id")
    return await _guard(lambda: client.state(entity_id))


class ServiceCall(BaseModel):
    domain: str = Field(min_length=1, max_length=64)
    service: str = Field(min_length=1, max_length=64)
    entity_id: str = ""
    data: dict = Field(default_factory=dict)


@router.post("/service")
async def service_call(auth: Auth, body: ServiceCall) -> dict:
    domain = body.domain.strip().lower()
    service = body.service.strip().lower()
    if not validators.is_domain(domain):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_domain")
    if not validators.is_service(service):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_service")

    payload = dict(body.data) if isinstance(body.data, dict) else {}
    entity_id = body.entity_id.strip().lower()
    if entity_id:
        if not validators.is_entity(entity_id):
            raise coded(status.HTTP_400_BAD_REQUEST, "invalid_entity_id")
        if validators.domain_of(entity_id) != domain:
            raise coded(status.HTTP_400_BAD_REQUEST, "entity_domain_mismatch")
        payload["entity_id"] = entity_id

    changed = await _guard(lambda: client.call_service(domain, service, payload))
    return {"changed": changed}


# --------------------------------------------------------------------------- #
# Favoriten (per-User, lokal in der HydraHive-DB)
# --------------------------------------------------------------------------- #
@router.get("/favorites")
def favorites(auth: Auth) -> list[dict]:
    user, _ = auth
    return favorites_store.list_for(user)


class FavoriteIn(BaseModel):
    entity_id: str = Field(min_length=1, max_length=255)


@router.post("/favorites")
def add_favorite(auth: Auth, body: FavoriteIn) -> dict:
    user, _ = auth
    entity_id = body.entity_id.strip().lower()
    if not validators.is_entity(entity_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_entity_id")
    try:
        return favorites_store.add(user, entity_id)
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "favorites_full")


@router.delete("/favorites/{entity_id}")
def remove_favorite(auth: Auth, entity_id: str) -> dict:
    user, _ = auth
    entity_id = entity_id.strip().lower()
    if not validators.is_entity(entity_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_entity_id")
    removed = favorites_store.remove(user, entity_id)
    return {"removed": removed}
