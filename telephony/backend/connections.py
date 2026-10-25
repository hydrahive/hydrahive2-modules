"""SIP-Verbindung je Nutzer: speichern, verbinden, trennen, löschen (PLAN-EINSTELLUNGEN Schritt 6).

Inhaber ist die stabile user_id. Das Kennwort wird verschlüsselt gespeichert und nie zurückgegeben. Verbunden wird mit
der geprüften Heimnetz-IP (netguard), nicht mit dem Namen. ``enabled`` merkt sich „Verbinden“ über Neustarts.
"""
from __future__ import annotations

import logging
import secrets as _rand
import time

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

from . import assistant, calls, conn_manager, netguard, secrets
from .conn_models import ConnectionIn

logger = logging.getLogger(__name__)
MANAGER = conn_manager.Manager()
_PUBLIC = ("pbx", "display_name", "registrar", "registrar_port", "username", "own_number", "local_sip_port",
           "rtp_port_min", "rtp_port_max", "register_interval", "status", "status_at", "created_at", "updated_at")
_WAIT = {"connecting", "disconnected"}


class NotFound(LookupError):
    pass


class Invalid(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _owner(user_id: str) -> str:
    return f"user:{user_id}"


def _resolve_target(host: str) -> str:
    return netguard.check(host)


def _bind_host() -> str:
    return "0.0.0.0"


def _row(owner: str):
    with db() as c:
        return c.execute("SELECT * FROM module_telephony_connections WHERE owner=?", (owner,)).fetchone()


def public(user_id: str) -> dict:
    r = _row(_owner(user_id))
    if not r:
        return {"configured": False, "status": "not_configured"}
    return {"configured": True, "has_password": True, "enabled": bool(r["enabled"]), **{k: r[k] for k in _PUBLIC},
            "answer_calls": bool(r["answer_calls"]), "greeting": r["greeting"],
            "greeting_default": calls.DEFAULT_GREETING, "test_until": calls.open_window(r),
            "call_mode": r["call_mode"], "assistant_name": r["assistant_name"],
            "assistant_knowledge": r["assistant_knowledge"], "assistant_model": r["assistant_model"]}


def save(user_id: str, data: ConnectionIn) -> dict:
    owner, now = _owner(user_id), now_iso()
    try:
        _resolve_target(data.registrar)
    except netguard.Blocked as e:
        raise Invalid("blocked", str(e)) from None
    old = _row(owner)
    if old is None and data.password is None:
        raise Invalid("password_required", "Kennwort fehlt")
    cid = old["id"] if old else _rand.token_hex(12)
    with db() as c:
        if data.local_sip_port and c.execute("SELECT 1 FROM module_telephony_connections WHERE local_sip_port=? "
                                             "AND owner<>?", (data.local_sip_port, owner)).fetchone():
            raise Invalid("port_taken", "Lokaler SIP-Port ist schon von einer anderen Verbindung belegt")
        secret = secrets.seal(cid, data.password.get_secret_value()) if data.password else old["secret"]
        fields = data.public()
        if old:
            c.execute("UPDATE module_telephony_connections SET " + ", ".join(f"{k}=?" for k in fields) +
                      ", secret=?, updated_at=? WHERE id=?", (*fields.values(), secret, now, cid))
        else:
            c.execute("INSERT INTO module_telephony_connections(id, owner, " + ", ".join(fields) +
                      ", secret, created_at, updated_at) VALUES (" + ",".join("?" * (len(fields) + 5)) + ")",
                      (cid, owner, *fields.values(), secret, now, now))
    row = _row(owner)
    if row["enabled"]:
        _start(row)                                     # geänderte Daten → neu anmelden
    return public(user_id)


def _set_status(cid: str, code: str) -> None:
    with db() as c:
        c.execute("UPDATE module_telephony_connections SET status=?, status_at=? WHERE id=?", (code, now_iso(), cid))
    logger.info("telephony: Verbindung %s → %s", cid[:6], code)


def _config(row) -> dict:
    return {"user": row["username"], "password": secrets.open_(row["id"], row["secret"]),
            "domain": row["registrar"], "target": (_resolve_target(row["registrar"]), row["registrar_port"]),
            "bind": (_bind_host(), row["local_sip_port"]), "display_name": row["display_name"],
            "interval": row["register_interval"], "rtp_ports": (row["rtp_port_min"], row["rtp_port_max"]),
            "call_policy": lambda cid=row["id"]: calls.policy(cid),
            "call_record": lambda info, cid=row["id"]: calls.record(cid, info),
            "call_assistant": lambda cid=row["id"]: assistant.bundle(cid)}


def _start(row) -> None:
    cid = row["id"]
    try:
        cfg = _config(row)
    except netguard.Blocked:
        MANAGER.stop(cid)
        _set_status(cid, "blocked")
        return
    except secrets.SecretError:
        MANAGER.stop(cid)
        _set_status(cid, "secret_invalid")
        return
    MANAGER.ensure(cid, cfg, lambda code: _set_status(cid, code))


def connect(user_id: str, wait: float = 10.0) -> dict:
    row = _row(_owner(user_id))
    if not row:
        raise NotFound(user_id)
    with db() as c:
        c.execute("UPDATE module_telephony_connections SET enabled=1, status='connecting', status_at=? WHERE id=?",
                  (now_iso(), row["id"]))
    MANAGER.stop(row["id"])                               # „Verbinden“ = frischer Versuch, auch nach Fehlern
    _start(_row(_owner(user_id)))
    end = time.monotonic() + wait
    while time.monotonic() < end and _row(_owner(user_id))["status"] in _WAIT:
        time.sleep(0.05)
    return public(user_id)


def disconnect(user_id: str) -> dict:
    row = _row(_owner(user_id))
    if not row:
        raise NotFound(user_id)
    with db() as c:
        c.execute("UPDATE module_telephony_connections SET enabled=0 WHERE id=?", (row["id"],))
    MANAGER.stop(row["id"])
    _set_status(row["id"], "disconnected")
    return public(user_id)


def delete(user_id: str) -> None:
    row = _row(_owner(user_id))
    if not row:
        raise NotFound(user_id)
    MANAGER.stop(row["id"])
    with db() as c:
        c.execute("DELETE FROM module_telephony_calls WHERE connection_id=?", (row["id"],))
        c.execute("DELETE FROM module_telephony_connections WHERE id=?", (row["id"],))


def reconcile() -> None:
    """Modul-Job: laufende Threads passend zu ``enabled`` halten (auch nach Neustart)."""
    with db() as c:
        rows = c.execute("SELECT * FROM module_telephony_connections").fetchall()
    wanted = {r["id"] for r in rows if r["enabled"]}
    for cid in set(MANAGER.running()) - wanted:
        MANAGER.stop(cid)
    for r in rows:
        if r["enabled"] and r["status"] not in ("auth_failed", "not_found", "blocked", "secret_invalid"):
            _start(r)
