"""S7: Bluetooth-Routen. Kiosk (ohne Login, Schlüssel + localhost) und Cockpit (Login + Recht module.vitrine).

Am Kiosk gibt es kein Entfernen (SPEC S7): niemand soll im Vorbeigehen die Tastatur entkoppeln.
Die Routen legen nur Aufträge ab; ausgeführt werden sie vom Vitrine-Dienst (renderer/bt_service.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from hydrahive.settings import settings
from renderer import config

from . import bluetooth

_ADDR = r"^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}$"
_STATUS = {"invalid_address": 422, "unavailable": 503, "window_closed": 409, "not_seen": 409, "not_paired": 409}

def _kiosk_enabled() -> None:
    """Im Cockpit abgeschaltet (bluetooth_enabled=false) → am Kiosk gibt es Bluetooth gar nicht, nicht nur keinen Knubbel."""
    if config.load(_data())["dashboard"].get("bluetooth_enabled") is False:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found"})


kiosk_router = APIRouter(dependencies=[Depends(_kiosk_enabled)])
cockpit_router = APIRouter()


class PairIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: str = Field(pattern=_ADDR)


def _data():
    return settings.data_dir / "vitrine"


def _fail(e: bluetooth.BtError):
    raise HTTPException(_STATUS.get(e.code, 409), detail={"code": e.code}) from None


def _view(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return bluetooth.view(_data())


def _scan() -> dict:
    try:
        return bluetooth.scan(_data())
    except bluetooth.BtError as e:
        _fail(e)


def _pair(body: PairIn) -> dict:
    try:
        bluetooth.pair(_data(), body.address)
    except bluetooth.BtError as e:
        _fail(e)
    return {"queued": True}


for r in (kiosk_router, cockpit_router):
    r.add_api_route("/bluetooth", _view, methods=["GET"])
    r.add_api_route("/bluetooth/scan", _scan, methods=["POST"])
    r.add_api_route("/bluetooth/pair", _pair, methods=["POST"], status_code=status.HTTP_202_ACCEPTED)


@cockpit_router.delete("/bluetooth/{address}", status_code=status.HTTP_202_ACCEPTED)
def remove(address: str) -> dict:
    """Nur Cockpit: gekoppeltes Gerät entfernen (Dienst ruft RemoveDevice)."""
    try:
        bluetooth.remove(_data(), address)
    except bluetooth.BtError as e:
        _fail(e)
    return {"queued": True}
