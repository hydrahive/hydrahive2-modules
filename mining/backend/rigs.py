"""Rigs: koppeln, freigeben, sperren, melden.

Ablauf (Spec §E2):
1. Admin legt Code an (pairing.create) → Rig tauscht ihn gegen ein Token (enroll).
2. Rig steht auf ``pending``; Meldungen werden angenommen, aber Soll ist ``stop``.
3. Admin gibt frei (approve) → ``active``. Sperren (revoke) löscht das Token sofort.
Tokens: 32 Byte zufällig, nur SHA-256 in der DB.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone

from hydrahive.db.connection import db

from . import pairing

TOKEN_PREFIX = "hhrig_"
MAX_REPORT_BYTES = 8192
_INFO_FIELDS = ("hostname", "os", "client_version", "gpu_vendor", "gpu_model", "gpu_mem_mb", "driver")


class RigError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def token_hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _clean_info(info: dict) -> dict:
    out: dict = {}
    for k in _INFO_FIELDS:
        v = info.get(k)
        if v is None:
            continue
        if k == "gpu_mem_mb":
            out[k] = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 10**7 else None
        else:
            out[k] = str(v)[:120]
    if out.get("gpu_vendor") not in (None, "nvidia", "amd", "none"):
        out["gpu_vendor"] = "unknown"
    return out


def enroll(code: str, info: dict, remote_ip: str) -> dict:
    """Code gegen Token tauschen. Einmalig; Name kommt vom Code, nicht vom Rig."""
    hashed = pairing.code_hash(code)
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    rig_id = str(uuid.uuid4())
    clean = _clean_info(info or {})
    # immediate: Schreibsperre vorab → zwei gleichzeitige Rigs können denselben
    # Code nicht beide verbrauchen. Fehler rollen alles zurück (Code bleibt frei).
    with db(immediate=True) as c:
        row = c.execute("SELECT name FROM module_mining_pairing WHERE code_hash = ?", (hashed,)).fetchone()
        if row is None or not pairing.consume(c, hashed):
            raise RigError("pairing_code_invalid")
        name = row["name"]
        if c.execute("SELECT 1 FROM module_mining_rigs WHERE name = ?", (name,)).fetchone():
            raise RigError("rig_name_taken")
        cols = ["id", "name", "status", "token_hash", "remote_ip", "created_at", "last_seen", *clean]
        vals = [rig_id, name, "pending", token_hash(token), remote_ip, _now(), _now(), *clean.values()]
        c.execute(f"INSERT INTO module_mining_rigs ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
    return {"rig_id": rig_id, "name": name, "token": token, "status": "pending"}


def by_token(token: str) -> dict | None:
    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    with db() as c:
        row = c.execute(
            "SELECT * FROM module_mining_rigs WHERE token_hash = ? AND status != 'revoked'",
            (token_hash(token),),
        ).fetchone()
    return dict(row) if row else None


def report(rig: dict, data: dict, remote_ip: str) -> None:
    raw = json.dumps(data.get("state") or {}, separators=(",", ":"))
    if len(raw) > MAX_REPORT_BYTES:
        raise RigError("report_too_large")
    clean = _clean_info(data.get("info") or {})
    sets = ["last_report = ?", "last_seen = ?", "remote_ip = ?", *(f"{k} = ?" for k in clean)]
    with db() as c:
        c.execute(f"UPDATE module_mining_rigs SET {', '.join(sets)} WHERE id = ?",
                  (raw, _now(), remote_ip, *clean.values(), rig["id"]))


def desired(rig: dict) -> dict:
    """Soll-Zustand für den Rig. E2: nur stop; Mining folgt mit E3/E4."""
    if rig["status"] != "active":
        return {"action": "stop", "reason": "awaiting_approval"}
    if not rig["enabled"]:
        return {"action": "stop", "reason": "disabled"}
    return {"action": "stop", "reason": "no_miner_yet"}


def list_rigs() -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT * FROM module_mining_rigs ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d.pop("token_hash", None)
        d["last_report"] = json.loads(d["last_report"]) if d.get("last_report") else None
        out.append(d)
    return out


def _update(rig_id: str, sql: str, *args) -> bool:
    with db() as c:
        return c.execute(f"UPDATE module_mining_rigs SET {sql} WHERE id = ?", (*args, rig_id)).rowcount == 1


def approve(rig_id: str) -> bool:
    return _update(rig_id, "status = 'active', approved_at = ?", _now()) if _is(rig_id, "pending") else False


def revoke(rig_id: str) -> bool:
    return _update(rig_id, "status = 'revoked', token_hash = NULL")


def set_enabled(rig_id: str, enabled: bool) -> bool:
    return _update(rig_id, "enabled = ?", int(bool(enabled)))


def delete(rig_id: str) -> bool:
    """Nur gesperrte Rigs löschen (Name wird wieder frei)."""
    with db() as c:
        return c.execute("DELETE FROM module_mining_rigs WHERE id = ? AND status = 'revoked'",
                         (rig_id,)).rowcount == 1


def _is(rig_id: str, status: str) -> bool:
    with db() as c:
        row = c.execute("SELECT status FROM module_mining_rigs WHERE id = ?", (rig_id,)).fetchone()
    return bool(row) and row["status"] == status
