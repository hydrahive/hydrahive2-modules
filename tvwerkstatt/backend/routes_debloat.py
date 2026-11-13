"""Schnittstellen Entrümpeln /api/modules/tvwerkstatt/devices/{id}/debloat… (Teil 1, nur lesend). Nur Admins."""
from __future__ import annotations

from fastapi import APIRouter, status

from . import debloat_jobs, jobs, state
from .routes_look import Admin, _guard, _known, _start

router = APIRouter()


@router.get("/devices/{device_id}/debloat")
def get_debloat(device_id: str, p: Admin) -> dict:
    """Zuletzt gelesener Stand mit Empfehlungen und Schutz, dazu der letzte Leseauftrag."""
    _known(device_id)
    dev = next(d for d in state.devices() if d["device_id"] == device_id)
    return {"view": debloat_jobs.view(device_id, dev.get("stock_home") or ""),
            "read_job": jobs.last_job("debloat_read", device_id)}


@router.post("/devices/{device_id}/debloat/read", status_code=status.HTTP_202_ACCEPTED)
async def read_debloat(device_id: str, p: Admin) -> dict:
    """Pakete vom Fernseher lesen (ändert am Fernseher nichts)."""
    _known(device_id)
    await _guard()
    return _start("debloat_read", device_id, p.username, debloat_jobs.run_read)
