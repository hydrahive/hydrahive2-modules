"""Rig-Verwaltung für Admins (unter /api/modules/mining, zusätzlich mining.control).

GET    /rigs                 Liste (ohne Tokens) inkl. Zuteilung
GET    /rigs/log             Wechsel-Protokoll (optional ?rig_id=)
GET    /rigs/power           Zustand der Energie-Steuerung
POST   /rigs/{id}/power      {"follows_power": bool, "priority": int}
GET    /rigs/{id}/benchmarks Messungen; POST …/benchmarks/reset = neu messen
GET    /rigs/history?hours=24 Verlauf fürs Diagramm (1–168 h)
POST   /rigs/pairing         Kopplungs-Code + fertiger Installationsbefehl
POST   /rigs/{id}/approve    freigeben
POST   /rigs/{id}/revoke     sperren (Token sofort ungültig)
POST   /rigs/{id}/enabled    an/aus  {"enabled": bool}
DELETE /rigs/{id}            gesperrten Rig löschen
"""
from __future__ import annotations

import shlex
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from . import history, pairing, power, rigs, runtime_store, store, tls_pin
from .access import Control

rig_router = APIRouter(prefix="/rigs")
HISTORY_POINTS = 300
CLIENT_URL = "https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/mining/rig/install.sh"


def _not_found(ok: bool) -> None:
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "rig_not_found_or_wrong_state"})


@rig_router.get("")
def list_rigs(_control: Control) -> list[dict]:
    return rigs.list_rigs()


@rig_router.post("/pairing")
def create_pairing(request: Request, _control: Control, body: dict[str, Any]) -> dict:
    try:
        created = pairing.create(str(body.get("name") or ""), created_by=None)
    except pairing.PairingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": str(exc)}) from exc
    host = request.headers.get("host") or request.url.netloc
    server = f"https://{host}"
    pin = tls_pin.server_pin(host)
    args = ["--server", server, "--code", created["code"]] + (["--pin", pin] if pin else [])
    cmd = f"curl -fsSL {CLIENT_URL} | sudo sh -s -- {shlex.join(args)}"
    return {**created, "server": server, "pin": pin, "command": cmd}


@rig_router.post("/{rig_id}/approve")
def approve(_control: Control, rig_id: str) -> dict:
    _not_found(rigs.approve(rig_id))
    return {"ok": True}


@rig_router.post("/{rig_id}/revoke")
def revoke(_control: Control, rig_id: str) -> dict:
    _not_found(rigs.revoke(rig_id))
    return {"ok": True}


@rig_router.post("/{rig_id}/enabled")
def set_enabled(_control: Control, rig_id: str, body: dict[str, Any]) -> dict:
    if not isinstance(body.get("enabled"), bool):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "enabled_must_be_bool"})
    _not_found(rigs.set_enabled(rig_id, body["enabled"]))
    return {"ok": True}


@rig_router.delete("/{rig_id}")
def delete(_control: Control, rig_id: str) -> dict:
    _not_found(rigs.delete(rig_id))
    return {"ok": True}


@rig_router.post("/{rig_id}/power")
def set_power(_control: Control, rig_id: str, body: dict[str, Any]) -> dict:
    fp, prio = body.get("follows_power"), body.get("priority", 0)
    if not isinstance(fp, bool) or isinstance(prio, bool) or not isinstance(prio, int) or not -100 <= prio <= 100:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "power_prefs_invalid"})
    _not_found(rigs.set_power_prefs(rig_id, fp, prio))
    return {"ok": True}


@rig_router.get("/{rig_id}/benchmarks")
def benchmarks(_control: Control, rig_id: str) -> list[dict]:
    return runtime_store.list_bench(rig_id)


@rig_router.post("/{rig_id}/benchmarks/reset")
def reset_benchmarks(_control: Control, rig_id: str) -> dict:
    """Neu messen (z. B. nach Treiber-Update oder Übertakten)."""
    runtime_store.clear_bench(rig_id)
    return {"ok": True}


@rig_router.get("/log")
def log(_control: Control, rig_id: str | None = None) -> list[dict]:
    return runtime_store.switch_log(rig_id)


@rig_router.get("/history")
def rig_history(_control: Control, hours: int = Query(24, ge=1, le=168)) -> dict:
    """Verlauf aller nicht gesperrten Rigs, je Rig höchstens ~300 Punkte."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = [{"id": r["id"], "name": r["name"],
            "points": history.downsample(history.points(r["id"], since=since), HISTORY_POINTS)}
           for r in rigs.list_rigs() if r["status"] != "revoked"]
    return {"hours": hours, "usd_per_eur": store.get_usd_per_eur(), "rigs": out}


@rig_router.get("/power")
def power_status(_control: Control) -> dict:
    return power.status()
