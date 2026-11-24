"""Multiseat M1: GET/PUT /seats (nur Admin). Zeigt Geräte, Vorschlag, Hinweis und den Schaltzustand (M2); speichert die
vom Admin bestätigte Zuordnung in <daten>/seats.json. Umgeschaltet wird nur über seat_apply_routes (POST apply/revert)."""
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


def _switch() -> dict:
    from .seat_apply_routes import status       # Zustand des Ein-/Ausschaltens (Marker, laufender Lauf, letzter Lauf)
    return status()


def _saved_error(snap: dict, saved: dict | None) -> str | None:
    """Gilt die gespeicherte Zuordnung noch für die Geräte von jetzt? (Knopf „einschalten“ nur dann)."""
    from . import seat_plan
    if not saved:
        return "vitrine_seat_not_saved"
    try:
        seat_plan.build_plan(snap, seats.validate(snap, saved.get("assignment")))
    except seats.SeatError as e:
        return e.code
    return None


@router.get("/seats")
def get_seats() -> dict:
    snap = snapshot()
    saved = _saved()
    return {"devices": {k: snap[k] for k in ("gpus", "sound", "inputs")}, "seats": snap["seats"],
            **seats.suggest(snap), "saved": saved, "saved_error": _saved_error(snap, saved), **_switch()}


class SeatsIn(BaseModel):
    assignment: Annotated[dict[str, str], Field(max_length=64)]


@router.put("/seats")
def put_seats(body: SeatsIn) -> dict:
    try:
        ok = seats.validate(snapshot(), body.assignment)
    except seats.SeatError as e:
        raise HTTPException(status_code=422, detail={"code": e.code}) from None
    data = {"assignment": ok, "saved_at": int(time.time())}
    old = _saved() or {}
    if isinstance(old.get("auto"), bool):
        data["auto"] = old["auto"]                      # N3: „Übernehmen“ behält den Vermerk ein/aus
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "seats.json.tmp"
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(d / "seats.json")
    return {**data, **_switch()}
