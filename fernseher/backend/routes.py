"""Routen /api/modules/fernseher/*. Der Schlüssel verlässt den Server nie (nur psk_set)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded

from . import client, settings_store, validators
from .access import Control
from .client_errors import TVError

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Admin = Annotated[tuple[str, str], Depends(require_admin)]

_HTTP = {"tv_not_configured": 503, "tv_unreachable": 504, "tv_needs_restart": 409, "tv_auth_failed": 502,
         "tv_upstream_error": 502, "tv_channel_unknown": 404, "tv_app_unknown": 404, "tv_channel_ambiguous": 409,
         "tv_volume_limit": 400, "tv_volume_invalid": 400}


async def _guard(call):
    try:
        return await call()
    except TVError as exc:
        raise coded(_HTTP.get(exc.code, 502), exc.code, message=str(exc))


class SettingsIn(BaseModel):
    name: str = Field(default="", max_length=80)
    address: str = Field(max_length=253)
    psk: str | None = Field(default=None, max_length=128)
    volume_limit: int = Field(default=settings_store.DEFAULT_LIMIT, ge=1, le=100)


@router.get("/settings")
def get_settings(auth: Auth) -> dict:
    return settings_store.public()


@router.put("/settings")
def put_settings(body: SettingsIn, admin: Admin) -> dict:
    try:
        out = settings_store.save(name=body.name, address=body.address, psk=(body.psk or "").strip() or None,
                                  volume_limit=body.volume_limit, user=admin[0])
    except validators.AddressError:
        raise coded(status.HTTP_400_BAD_REQUEST, "tv_address_not_local")
    except ValueError as exc:
        if str(exc) == "psk_missing":
            raise coded(status.HTTP_400_BAD_REQUEST, "tv_psk_missing")
        raise coded(status.HTTP_400_BAD_REQUEST, "tv_settings_invalid")
    client.clear_cache()
    return out


@router.post("/test")
async def test(admin: Admin) -> dict:
    return await _guard(client.test)


@router.get("/status")
async def get_status(auth: Auth) -> dict:
    return await _guard(client.status)


@router.get("/channels")
async def get_channels(auth: Auth) -> list[dict]:
    chs = await _guard(client.channels)
    return [{"number": c["number"], "name": c["name"]} for c in chs]


@router.get("/apps")
async def get_apps(auth: Auth) -> list[dict]:
    return await _guard(client.apps)


class ChannelIn(BaseModel):
    sender: str = Field(min_length=1, max_length=60)


class VolumeIn(BaseModel):
    wert: str = Field(min_length=1, max_length=5)


class MuteIn(BaseModel):
    stumm: bool


class PowerIn(BaseModel):
    an: bool


class AppIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


@router.post("/channel")
async def post_channel(body: ChannelIn, ctl: Control) -> dict:
    return await _guard(lambda: client.set_channel(body.sender))


@router.post("/volume")
async def post_volume(body: VolumeIn, ctl: Control) -> dict:
    return await _guard(lambda: client.set_volume(body.wert))


@router.post("/mute")
async def post_mute(body: MuteIn, ctl: Control) -> dict:
    return await _guard(lambda: client.set_mute(body.stumm))


@router.post("/power")
async def post_power(body: PowerIn, ctl: Control) -> dict:
    return await _guard(lambda: client.set_power(body.an))


@router.post("/app")
async def post_app(body: AppIn, ctl: Control) -> dict:
    return await _guard(lambda: client.start_app(body.name))
