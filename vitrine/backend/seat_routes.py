"""Multiseat M1: GET/PUT /seats (nur Admin). Zeigt Geräte, Vorschlag und Hinweis; speichert die vom Admin bestätigte
Zuordnung in <daten>/seats.json. Angewendet wird sie erst mit M2 (Installer) – hier wird nichts umgeschaltet."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from hydrahive.api.middleware.auth import require_admin
from hydrahive.settings import settings
from pydantic import BaseModel, Field

from . import seats, seats_snapshot

router = APIRouter(dependencies=[Depends(require_admin)])
SYS_ROOT = Path("/")


def data_dir() -> Path:
    return settings.data_dir / "vitrine"


def _vitrine_bt(data: Path) -> list[str]:
    """Über die Vitrine gekoppelte Bluetooth-Geräte (renderer/bt_service.py schreibt bt/state.json)."""
    from renderer import bt_jobs
    s = bt_jobs.read_state(data) or {}
    return [str(d.get("address", "")) for d in s.get("devices") or [] if isinstance(d, dict) and d.get("paired")]


def snapshot() -> dict:
    return seats_snapshot.read(SYS_ROOT, vitrine_bt=_vitrine_bt(data_dir()))


def _saved() -> dict | None:
    try:
        raw = json.loads((data_dir() / "seats.json").read_text())
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


@router.get("/seats")
def get_seats() -> dict:
    snap = snapshot()
    return {"devices": {k: snap[k] for k in ("gpus", "sound", "inputs")}, "seats": snap["seats"],
            **seats.suggest(snap), "saved": _saved(), "applied": False}


class SeatsIn(BaseModel):
    assignment: Annotated[dict[str, str], Field(max_length=64)]


@router.put("/seats")
def put_seats(body: SeatsIn) -> dict:
    try:
        ok = seats.validate(snapshot(), body.assignment)
    except seats.SeatError as e:
        raise HTTPException(status_code=422, detail={"code": e.code}) from None
    data = {"assignment": ok, "saved_at": int(time.time())}
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "seats.json.tmp"
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(d / "seats.json")
    return {**data, "applied": False}
