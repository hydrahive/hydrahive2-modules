"""Multiseat M2: Zweiten Arbeitsplatz ein-/ausschalten (POST /seats/apply, /seats/revert; nur Admin).

Ablauf apply: gespeicherte Zuordnung (seats.json) gegen den AKTUELLEN Snapshot prüfen (seats.validate +
seat_plan.build_plan), die drei Dateien nach <daten>/multiseat/ schreiben und multiseat-apply.sh über den einzigen
erlaubten Root-Weg starten (`sudo -n bash -c "systemd-run … /bin/bash '<skript>' …"`, Muster install.sh). Alle Pfade
kommen aus dem Modul bzw. dem Datenordner, nie aus der Anfrage. Ein Lauf gleichzeitig (sonst 409); Ergebnis in
<daten>/multiseat/last-run.json.

`applied` liest den Marker direkt: /etc/hydrahive2-vitrine ist 755 (kiosk-install.sh `install -d -m 755`), der Marker
644 (umask von root). Das ist der einfachste sichere Weg – kein sudo für eine reine Statusanzeige.
"""
from __future__ import annotations

import subprocess  # noqa: F401 – Tests ersetzen subprocess.run (seat_auto nutzt dasselbe Modul)
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from hydrahive.api.middleware.auth import require_admin

from . import seat_auto, seat_plan, seats
from .seat_routes import _saved, data_dir, snapshot

router = APIRouter(dependencies=[Depends(require_admin)])
MODULE_ROOT = Path(__file__).resolve().parents[1]
ETC = Path("/etc/hydrahive2-vitrine")
_lock = threading.Lock()
_running: dict[str, str | None] = {"action": None}


def run_dir() -> Path:
    return data_dir() / "multiseat"


def marker() -> Path:
    return ETC / "multiseat.aktiv"


def revert_script() -> Path:
    return ETC / "multiseat-revert.sh"


root_cmd = seat_auto.root_cmd          # derselbe Root-Weg wie die Automatik beim Update (§7 N2a)


def last_run() -> dict | None:
    import json
    try:
        raw = json.loads((run_dir() / "last-run.json").read_text())
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def status() -> dict:
    return {"applied": marker().is_file(), "running": _running["action"], "last_run": last_run()}


def _execute(action: str, cmd: list[str]) -> None:
    try:
        seat_auto.execute(action, cmd, run_dir())
    finally:
        _running["action"] = None
        _lock.release()


def _start(action: str, cmd: list[str]) -> None:
    t = threading.Thread(target=_execute, args=(action, cmd), name=f"vitrine-multiseat-{action}", daemon=True)
    t.start()


def _claim(action: str) -> None:
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail={"code": "vitrine_seat_busy"})
    _running["action"] = action


@router.post("/seats/apply")
def apply_seats() -> dict:
    saved = _saved()
    if not saved or not isinstance(saved.get("assignment"), dict):
        raise HTTPException(status_code=422, detail={"code": "vitrine_seat_not_saved"})
    if marker().is_file():
        raise HTTPException(status_code=409, detail={"code": "vitrine_seat_already_on"})
    snap = snapshot()
    try:
        plan = seat_plan.build_plan(snap, seats.validate(snap, saved["assignment"]))
    except seats.SeatError as e:
        raise HTTPException(status_code=422, detail={"code": e.code}) from None
    _claim("apply")
    try:
        seat_auto.set_auto(data_dir(), True)            # N3: bewusst eingeschaltet → Updates dürfen wieder einschalten
        files = seat_auto.write_plan_files(run_dir(), plan)
        _start("apply", root_cmd(MODULE_ROOT / "extension" / "multiseat-apply.sh", *files))
    except BaseException:
        _running["action"] = None
        _lock.release()
        raise
    return {**status(), "running": "apply"}


@router.post("/seats/revert")
def revert_seats() -> dict:
    if not revert_script().is_file():
        raise HTTPException(status_code=409, detail={"code": "vitrine_seat_not_on"})
    _claim("revert")
    try:
        seat_auto.set_auto(data_dir(), False)           # N3: bewusst ausgeschaltet → das nächste Update schaltet nicht ein
        _start("revert", root_cmd(revert_script()))
    except BaseException:
        _running["action"] = None
        _lock.release()
        raise
    return {**status(), "running": "revert"}
