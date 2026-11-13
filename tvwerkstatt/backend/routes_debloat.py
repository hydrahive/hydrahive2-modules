"""Schnittstellen Entrümpeln /api/modules/tvwerkstatt/devices/{id}/debloat… Nur Admins.

Lesen ändert nichts. Ab- und Einschalten nur mit Rückfrage-Kennzeichen; gesperrte Pakete werden schon hier abgelehnt,
die Schutzprüfung am Gerät folgt im Auftrag (backend/debloat_switch_jobs.py).
"""
from __future__ import annotations

from fastapi import APIRouter, status
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import debloat_jobs, debloat_switch, debloat_switch_jobs, jobs, state
from .routes_look import Admin, _guard, _known, _start

router = APIRouter()
SJ = debloat_switch_jobs


class Switch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    confirm: bool = False
    packages: list[str] | None = None


@router.get("/devices/{device_id}/debloat")
def get_debloat(device_id: str, p: Admin) -> dict:
    """Zuletzt gelesener Stand mit Empfehlungen und Schutz, Vermerke der Werkstatt, Sicherung, letzte Aufträge."""
    _known(device_id)
    dev = next(d for d in state.devices() if d["device_id"] == device_id)
    view = debloat_jobs.view(device_id, dev.get("stock_home") or "")
    mine = SJ.ours(device_id)
    if view is not None:
        on_now = {r["package"] for r in view["packages"] if r["state"] == "on"}
        view = {**view, "ours": mine, "back_on": [x for x in mine if x in on_now]}
    backup = SJ.backup_of(device_id)
    last = [j for j in (jobs.last_job(k, device_id) for k in ("debloat_off", "debloat_on")) if j]
    return {"view": view, "read_job": jobs.last_job("debloat_read", device_id),
            "switch_job": max(last, key=lambda j: j["created_at"]) if last else None,
            "backup_at": backup["taken_at"] if backup else ""}


@router.post("/devices/{device_id}/debloat/read", status_code=status.HTTP_202_ACCEPTED)
async def read_debloat(device_id: str, p: Admin) -> dict:
    """Pakete vom Fernseher lesen (ändert am Fernseher nichts). Auch „Nach Update prüfen“."""
    _known(device_id)
    await _guard()
    return _start("debloat_read", device_id, p.username, debloat_jobs.run_read)


async def _switch(device_id: str, p: Admin, body: Switch, *, on: bool) -> dict:
    _known(device_id)
    if not body.confirm:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_confirm_required")
    if not on and body.packages is None:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_debloat_bad_package")
    try:
        pkgs = SJ.prepare(device_id, body.packages, on=on)
    except debloat_switch.TvwDebloatError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None
    await _guard()

    async def runner(job_id: str, dev_id: str) -> None:
        await SJ.run_switch(job_id, dev_id, pkgs, on)
    return _start("debloat_on" if on else "debloat_off", device_id, p.username, runner)


@router.post("/devices/{device_id}/debloat/off", status_code=status.HTTP_202_ACCEPTED)
async def switch_off(device_id: str, p: Admin, body: Switch) -> dict:
    """Gewählte Pakete abschalten (nicht deinstallieren)."""
    return await _switch(device_id, p, body, on=False)


@router.post("/devices/{device_id}/debloat/on", status_code=status.HTTP_202_ACCEPTED)
async def switch_on(device_id: str, p: Admin, body: Switch) -> dict:
    """Gewählte Pakete einschalten; ohne Liste = „Alles zurück“ (alles, was die Werkstatt abgeschaltet hat)."""
    return await _switch(device_id, p, body, on=True)
