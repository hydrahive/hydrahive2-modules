"""S7: Dateien zwischen Backend und Dienst für Bluetooth (wie config.json/inbox – kein Socket, kein Port).

  <daten>/bt/inbox/<zeit>-<zufall>.json   Aufträge vom Backend: scan | pair <Adresse> | remove <Adresse>
  <daten>/bt/state.json                   Stand vom Dienst (Adapter, Fenster, Geräte, Code, Fehler)

Eigener Ordner: `<daten>/inbox/` gehört den Meldungen (S3).
"""
from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

from .bt_model import address

KINDS = ("scan", "pair", "remove")
MAX_JOBS = 20


class JobError(ValueError):
    pass


def _dir(data: Path) -> Path:
    return data / "bt"


def _inbox(data: Path) -> Path:
    return _dir(data) / "inbox"


def _atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(json.dumps(payload))
    tmp.replace(path)


def _valid(job: object) -> dict | None:
    if not isinstance(job, dict) or job.get("kind") not in KINDS:
        return None
    if job["kind"] == "scan":
        return {"kind": "scan", "address": None, "created": job.get("created")}
    addr = address(job.get("address"))
    return {"kind": job["kind"], "address": addr, "created": job.get("created")} if addr else None


def put(data: Path, kind: str, addr: str | None = None, *, now: float | None = None) -> None:
    """Auftrag ablegen. Ungültig → JobError (nichts geschrieben). Mehr als MAX_JOBS offene → die ältesten fallen weg."""
    now = time.time() if now is None else now
    job = _valid({"kind": kind, "address": addr.upper() if isinstance(addr, str) else addr, "created": now})
    if job is None or (kind == "scan" and addr is not None):
        raise JobError("ungültiger Bluetooth-Auftrag")
    _atomic(_inbox(data) / f"{now:017.6f}-{secrets.token_hex(4)}.json", job)
    files = sorted(_inbox(data).glob("*.json"))
    for old in files[: max(0, len(files) - MAX_JOBS)]:
        old.unlink(missing_ok=True)


def pending(data: Path, kind: str) -> bool:
    """Liegt schon ein gültiger Auftrag dieser Art? (nur lesen, nichts löschen)"""
    try:
        files = list(_inbox(data).glob("*.json"))
    except OSError:
        return False
    for p in files:
        try:
            job = _valid(json.loads(p.read_text()))
        except (OSError, ValueError):
            continue
        if job and job["kind"] == kind:
            return True
    return False


def take(data: Path) -> list[dict]:
    """Alle offenen Aufträge, älteste zuerst. Jede Datei wird gelöscht – auch kaputte (nie zweimal ausgeführt)."""
    out = []
    try:
        files = sorted(_inbox(data).glob("*.json"))
    except OSError:
        return []
    for p in files:
        try:
            job = _valid(json.loads(p.read_text()))
        except (OSError, ValueError):
            job = None
        p.unlink(missing_ok=True)
        if job:
            out.append(job)
    return out


def write_state(data: Path, state: dict, *, now: float | None = None) -> None:
    _atomic(_dir(data) / "state.json", {**state, "updated": time.time() if now is None else now})


def read_state(data: Path) -> dict | None:
    try:
        s = json.loads((_dir(data) / "state.json").read_text())
    except (OSError, ValueError):
        return None
    return s if isinstance(s, dict) else None
