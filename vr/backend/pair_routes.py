"""Kopplung: Code + QR anlegen (Login), Brillen verwalten (Login), Code einlösen (Gerät).

Login-Routen unter /api/modules/vr/pairing…, das Einlösen unter
/api/module-device/vr/redeem (ohne Nutzer-Login, mit Rate-Limit des Kerns).
"""
from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Request, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from . import pairing, qr_matrix, tls_pin

logger = logging.getLogger(__name__)
router = APIRouter()
device_router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


class PairIn(BaseModel):
    name: str = Field(default="Quest", max_length=40)


@router.post("/pairing")
def create_pairing(body: PairIn, request: Request, auth: Auth) -> dict:
    """Einmal-Code für den angemeldeten Nutzer + QR (SVG). Der QR enthält keinen API-Key."""
    try:
        created = pairing.create(auth[0], body.name)
    except pairing.PairingError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))
    host = request.headers.get("host") or request.url.netloc
    server = f"https://{host}"
    pin = tls_pin.server_pin(host) or ""
    payload = f"hydravr://pair?s={quote(server, safe=':/')}&c={created['code']}&p={quote(pin, safe='')}"
    # Matrix statt SVG-Text: das Cockpit zeichnet sie selbst (kein HTML einschleusbar).
    return {**created, "server": server, "pinned": bool(pin), "qr": qr_matrix.matrix(payload)}


@router.get("/headsets")
def headsets(auth: Auth) -> list[dict]:
    return pairing.list_headsets(auth[0])


@router.delete("/headsets/{hid}")
def remove(hid: str, auth: Auth) -> dict:
    from hydrahive.api.middleware import api_keys
    key_id = pairing.remove_headset(auth[0], hid)
    if key_id is None:
        raise coded(status.HTTP_404_NOT_FOUND, "headset_not_found")
    api_keys.delete(key_id, username=auth[0])       # Key der Brille sofort ungültig
    return {"ok": True}


def device_auth(x_vr_pair: str | None = Header(None, max_length=40)) -> str:
    """Geräte-Auth fürs Einlösen: nur ein syntaktisch passender Code im Header kommt durch."""
    if not x_vr_pair or len(pairing.normalize(x_vr_pair)) != pairing.CODE_LEN:
        raise coded(status.HTTP_401_UNAUTHORIZED, "pairing_code_required")
    return x_vr_pair


@device_router.post("/redeem")
def redeem(code: Annotated[str, Depends(device_auth)]) -> dict:
    """Brille löst den Code ein und bekommt EINMALIG ihren API-Key (Rolle des Nutzers)."""
    from hydrahive.api.middleware import api_keys
    from hydrahive.api.middleware.users import get_by_username
    try:
        hit = pairing.redeem(code)
    except pairing.PairingError:
        raise coded(status.HTTP_401_UNAUTHORIZED, "code_invalid")
    user = get_by_username(hit["username"])
    if not user:                                     # Nutzer inzwischen gelöscht
        raise coded(status.HTTP_401_UNAUTHORIZED, "code_invalid")
    key = api_keys.create(f"vr:{hit['name']}", user["username"], user["role"], user_id=user["user_id"])
    key_id = key[len(api_keys.PREFIX):len(api_keys.PREFIX) + 16]
    headset = pairing.add_headset(user["username"], hit["name"], key_id)
    logger.info("VR: Brille '%s' für %s gekoppelt", hit["name"], user["username"])
    return {"api_key": key, "username": user["username"], "headset": headset}
