"""Einrichten (network.configure): Zugänge (nur Namen aus dem Safe), Zertifikat bestätigen, testen, Import, Abruf."""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from hydrahive.access.deps import require_capability
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from . import collect, config_store, creds, importer, netcheck, pinned
from .errors import NetError
from .unifi_client import Udm

router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_capability("network.configure"))]
_HTTP = {"network_not_configured": 409, "network_cert_unconfirmed": 409, "network_cert_changed": 409,
         "network_fingerprint_mismatch": 409, "network_unreachable": 502, "network_auth_failed": 502,
         "network_bad_response": 502}
MAX_IMPORT = 50 * 1024 * 1024


def _fail(e: NetError):
    return coded(_HTTP.get(e.code, status.HTTP_400_BAD_REQUEST), e.code)


class SettingsIn(BaseModel):
    udm_url: str = Field(default="", max_length=200)
    udm_credential: str = Field(default="", max_length=60)
    fritz_host: str = Field(default="", max_length=120)
    fritz_credential: str = Field(default="", max_length=60)
    plan_down_mbit: float | None = None
    plan_up_mbit: float | None = None
    plan_price_eur: float | None = None


class ConfirmIn(BaseModel):
    fingerprint: str = Field(pattern="^[0-9a-f]{64}$")


def public(cfg: dict | None) -> dict:
    keys = ("udm_url", "udm_credential", "udm_pin", "fritz_host", "fritz_credential", "plan_down_mbit",
            "plan_up_mbit", "plan_price_eur", "last_full_sync", "last_error")
    return {k: (cfg or {}).get(k) for k in keys}


def _checked(b: SettingsIn, owner: str) -> dict:
    for v in (b.plan_down_mbit, b.plan_up_mbit, b.plan_price_eur):
        if v is not None and not 0 <= v <= 100_000:
            raise NetError("network_value_invalid")
    netcheck.udm_url(b.udm_url)
    creds.udm_key(owner, b.udm_credential)
    if b.fritz_host:
        netcheck.local_host(b.fritz_host)
    if b.fritz_credential:
        creds.fritz_login(owner, b.fritz_credential)
    return {**b.model_dump(), "udm_url": b.udm_url.strip().rstrip("/"), "fritz_host": b.fritz_host.strip() or None,
            "fritz_credential": b.fritz_credential or None}


def _cfg() -> dict:
    cfg = config_store.get()
    if not cfg or not cfg.get("udm_url"):
        raise NetError("network_not_configured")
    return cfg


@router.get("/settings")
def get_settings(p: Admin):
    return public(config_store.get())


@router.put("/settings")
def put_settings(body: SettingsIn, p: Admin):
    try:
        values = _checked(body, p.username)
    except NetError as e:
        raise _fail(e) from None
    return public(config_store.save(owner=p.username, **values))


@router.get("/credentials")
def get_credentials(p: Admin):
    return {"items": creds.names(p.username)}


@router.post("/udm/fingerprint")
async def udm_fingerprint(p: Admin):
    try:
        host, port = netcheck.udm_url(_cfg()["udm_url"])
        fp = await pinned.fetch_fingerprint(host, port)
    except NetError as e:
        raise _fail(e) from None
    except (OSError, TimeoutError, ValueError):
        raise _fail(NetError("network_unreachable")) from None
    return {"fingerprint": fp, "pretty": pinned.pretty(fp)}


@router.post("/udm/confirm")
async def udm_confirm(body: ConfirmIn, p: Admin):
    try:
        host, port = netcheck.udm_url(_cfg()["udm_url"])
        fp = await pinned.fetch_fingerprint(host, port)
    except NetError as e:
        raise _fail(e) from None
    except (OSError, TimeoutError, ValueError):
        raise _fail(NetError("network_unreachable")) from None
    if fp != body.fingerprint:
        raise _fail(NetError("network_fingerprint_mismatch"))
    config_store.set_pin(fp)
    return public(config_store.get())


@router.post("/udm/test")
async def udm_test(p: Admin):
    try:
        cfg = _cfg()
        info = await Udm(cfg["udm_url"], creds.udm_key(cfg["owner"], cfg["udm_credential"]),
                         cfg.get("udm_pin")).get("/proxy/network/integration/v1/info")
    except NetError as e:
        raise _fail(e) from None
    return {"ok": True, "version": (info or {}).get("applicationVersion")}


@router.post("/sync")
async def sync_now(p: Admin):
    await collect.tick_udm(now=int(time.time()))
    return await collect.tick_hourly(now=int(time.time()))


@router.post("/import")
async def import_snapshot(p: Admin, file: Annotated[UploadFile, File()]):
    raw = await file.read(MAX_IMPORT + 1)
    try:
        if len(raw) > MAX_IMPORT:
            raise NetError("network_import_invalid")
        return importer.load(raw)
    except NetError as e:
        raise _fail(e) from None
