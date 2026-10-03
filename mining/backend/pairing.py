"""Kopplungs-Codes: einmalig, 15 min gültig, nur als Hash gespeichert.

Format für Menschen: ``XXXX-XXXX-XXXX`` aus einem Alphabet ohne
Verwechsler (kein 0/O, 1/I/L). 31^12 ≈ 2^59 Möglichkeiten; zusammen mit dem
Rate-Limit des Kerns und der kurzen Laufzeit nicht durchprobierbar.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 12
TTL_MINUTES = 15
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")  # wird auch Kryptex-Worker-Name


class PairingError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize(code: str) -> str:
    return re.sub(r"[\s-]", "", code or "").upper()


def code_hash(code: str) -> str:
    return hashlib.sha256(normalize(code).encode("ascii", "ignore")).hexdigest()


def _pretty(raw: str) -> str:
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def create(name: str, created_by: str | None) -> dict:
    """Neuen Code für einen Rig-Namen anlegen. Gibt den Klartext genau einmal zurück."""
    if not NAME_RE.match(name or ""):
        raise PairingError("rig_name_invalid")
    raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
    now = _now()
    expires = now + timedelta(minutes=TTL_MINUTES)
    with db() as c:
        c.execute(
            "INSERT INTO module_mining_pairing (code_hash, name, expires_at, created_by, created_at)"
            " VALUES (?,?,?,?,?)",
            (code_hash(raw), name, expires.isoformat(), created_by, now.isoformat()),
        )
    return {"code": _pretty(raw), "name": name, "expires_at": expires.isoformat()}


def peek(code: str) -> dict | None:
    """Gültigen, unbenutzten Code nachschlagen, ohne ihn zu verbrauchen."""
    if len(normalize(code)) != CODE_LEN:
        return None
    with db() as c:
        row = c.execute(
            "SELECT code_hash, name FROM module_mining_pairing"
            " WHERE code_hash = ? AND used_at IS NULL AND expires_at > ?",
            (code_hash(code), _now().isoformat()),
        ).fetchone()
    return dict(row) if row else None


def consume(conn, hashed: str) -> bool:
    """Code atomar verbrauchen (in der Transaktion des Aufrufers). True = war gültig."""
    cur = conn.execute(
        "UPDATE module_mining_pairing SET used_at = ?"
        " WHERE code_hash = ? AND used_at IS NULL AND expires_at > ?",
        (_now().isoformat(), hashed, _now().isoformat()),
    )
    return cur.rowcount == 1
