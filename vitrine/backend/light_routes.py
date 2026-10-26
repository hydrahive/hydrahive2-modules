"""S8 Licht im Cockpit: Stand lesen und Vorschau starten (Login + Recht module.vitrine über das Modul-Tor).

Die Routen setzen das Licht nie selbst; sie lesen <daten>/light.json (schreibt der Licht-Thread im Vitrine-Dienst) bzw.
legen <daten>/light_preview.json ab.
"""
from __future__ import annotations

import json

from fastapi import APIRouter

from hydrahive.settings import settings
from renderer import light_preview

from .schemas import LightPreviewIn

router = APIRouter()
_KEYS = ("device", "state", "color", "effect", "label", "preview", "error", "updated")


def _data():
    return settings.data_dir / "vitrine"


@router.get("/light")
def light_status() -> dict:
    try:
        raw = json.loads((_data() / "light.json").read_text())
    except (OSError, ValueError):
        return {"available": False}
    if not isinstance(raw, dict):
        return {"available": False}
    return {"available": True, **{k: raw.get(k) for k in _KEYS}, "preview_states": list(light_preview.STATES)}


@router.post("/light/preview")
def light_preview_start(body: LightPreviewIn) -> dict:
    raw = light_preview.start(_data(), body.state)
    return {"state": raw["state"], "seconds": light_preview.SECONDS}
