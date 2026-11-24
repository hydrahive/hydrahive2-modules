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

import json
import shlex
import subprocess
import threading
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from hydrahive.api.middleware.auth import require_admin

from . import seat_plan, seats
from .seat_routes import _saved, data_dir, snapshot

router = APIRouter(dependencies=[Depends(require_admin)])
MODULE_ROOT = Path(__file__).resolve().parents[1]
ETC = Path("/etc/hydrahive2-vitrine")
TIMEOUT = 900                         # apply: apt + Prüfung 90 s; der Rückbau-Timer greift nach 300 s ohnehin
_lock = threading.Lock()
_running: dict[str, str | None] = {"action": None}


def run_dir() -> Path:
    return data_dir() / "multiseat"


def marker() -> Path:
    return ETC / "multiseat.aktiv"


def revert_script() -> Path:
    return ETC / "multiseat-revert.sh"


def root_cmd(script: Path, *args: Path) -> list[str]:
    """Root-Weg wie install.sh:59 – systemd-run, damit das Skript außerhalb der Dienst-Sandbox läuft."""
    inner = " ".join(["systemd-run --quiet --wait --pipe --collect /bin/bash", *(shlex.quote(str(p)) for p in (script, *args))])
    return ["sudo", "-n", "bash", "-c", inner]


def last_run() -> dict | None:
    try:
        raw = json.loads((run_dir() / "last-run.json").read_text())
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def status() -> dict:
    return {"applied": marker().is_file(), "running": _running["action"], "last_run": last_run()}


def _write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.chmod(0o644)
    tmp.replace(path)


def _execute(action: str, cmd: list[str]) -> None:
    started = int(time.time())
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, check=False)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = -1, "Zeitüberschreitung – der Rückbau-Timer stellt den Stand von vorher wieder her."
    except OSError as e:
        code, out = -1, f"Start fehlgeschlagen: {e}"
    res = {"action": action, "started": started, "finished": int(time.time()), "exit": code,
           "ok": code == 0, "lines": out.splitlines()[-40:]}
    try:
        _write(run_dir() / "last-run.json", json.dumps(res, indent=2))
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
        d = run_dir()
        d.mkdir(parents=True, exist_ok=True)
        files = (d / "plan.json", d / "lightdm.conf", d / "xorg.conf")
        _write(files[0], seat_plan.plan_json(plan))
        _write(files[1], seat_plan.render_lightdm(plan))
        _write(files[2], seat_plan.render_xorg(plan))
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
        _start("revert", root_cmd(revert_script()))
    except BaseException:
        _running["action"] = None
        _lock.release()
        raise
    return {**status(), "running": "revert"}
