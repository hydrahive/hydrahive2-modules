"""Geräte-Routen für den Kiosk-Browser (ohne Login): Kern hängt sie unter /api/module-device/vitrine ein,
mit Rate-Limit und der Prüfung `kiosk_auth` vor jeder Route (siehe hydrahive/api/module_devices.py)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from hydrahive.settings import settings
from renderer import config, inbox

from . import dash_data, kiosk

device_router = APIRouter()


def _data():
    return settings.data_dir / "vitrine"


def kiosk_auth(request: Request, k: str | None = Query(None, max_length=256)) -> None:
    # direkte Verbindung prüfen, nicht X-Forwarded-For: der Kiosk spricht HydraHive direkt auf 127.0.0.1 an
    host = request.client.host if request.client else None
    if not (kiosk.local_ok(host) and kiosk.key_ok(_data(), k)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found"})


@device_router.get("/kiosk", response_class=HTMLResponse)
def kiosk_page(k: str = Query(..., max_length=256)) -> HTMLResponse:
    return HTMLResponse(kiosk.page(k), headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@device_router.post("/back", status_code=status.HTTP_204_NO_CONTENT)
def kiosk_back() -> None:
    kiosk.back(_data())


@device_router.get("/data")
def kiosk_data(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    cfg = config.load(_data())
    return dash_data.build(_data(), cfg["dashboard"], return_seconds=cfg["dashboard_return_seconds"])


class ReadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[0-9a-f]{12}$")


@device_router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
def kiosk_read(body: ReadIn) -> None:
    """S3: Meldung als gelesen markieren – neben „Zurück“ die einzige ändernde Kiosk-Route."""
    if not inbox.mark_read(_data(), body.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found"})
    dash_data.invalidate("messages")
