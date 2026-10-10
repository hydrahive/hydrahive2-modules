"""Brillen koppeln: Einmal-Code (QR) → eigener API-Key der Brille.

- Code: 12 Zeichen ohne Verwechsler, 10 min gültig, nur als SHA-256 gespeichert,
  wird beim Einlösen atomar verbraucht (zweites Einlösen schlägt fehl).
- Der API-Key wird für den Nutzer erzeugt, der den Code angelegt hat, mit
  dessen aktueller Rolle. Klartext NUR in der Antwort an die Brille.
- Gekoppelte Brillen stehen in einer eigenen Tabelle (Name, Key-ID, Zeitpunkte),
  Entfernen löscht den Key im Kern sofort.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 12
TTL_MINUTES = 10
MAX_OPEN_CODES = 5            # je Nutzer gleichzeitig offen
NAME_RE = re.compile(r"^[\w .\-]{1,40}$")


class PairingError(ValueError):
    """Fachlicher Fehler (Code ungültig/abgelaufen, Name ungültig …)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(code or "").upper())


def code_hash(code: str) -> str:
    return hashlib.sha256(normalize(code).encode("ascii", "ignore")).hexdigest()


def pretty(raw: str) -> str:
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def create(user: str, name: str) -> dict:
    """Neuen Einmal-Code für [user] anlegen."""
    name = (name or "Quest").strip()
    if not NAME_RE.match(name):
        raise PairingError("name_invalid")
    now = _now()
    with db() as c:
        open_codes = c.execute(
            "SELECT COUNT(*) FROM module_vr_pairing WHERE username = ? AND used_at IS NULL AND expires_at > ?",
            (user, now.isoformat())).fetchone()[0]
        if open_codes >= MAX_OPEN_CODES:
            raise PairingError("too_many_open_codes")
        raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
        expires = now + timedelta(minutes=TTL_MINUTES)
        c.execute("INSERT INTO module_vr_pairing (code_hash, username, name, expires_at, created_at)"
                  " VALUES (?, ?, ?, ?, ?)", (code_hash(raw), user, name, expires.isoformat(), now.isoformat()))
    return {"code": pretty(raw), "name": name, "expires_at": expires.isoformat()}


def redeem(code: str) -> dict:
    """Code einlösen: verbraucht ihn atomar und liefert {username, name}. Wirft PairingError."""
    if len(normalize(code)) != CODE_LEN:
        raise PairingError("code_invalid")
    now = _now().isoformat()
    with db() as c:
        row = c.execute("SELECT username, name FROM module_vr_pairing"
                        " WHERE code_hash = ? AND used_at IS NULL AND expires_at > ?",
                        (code_hash(code), now)).fetchone()
        if not row:
            raise PairingError("code_invalid")
        cur = c.execute("UPDATE module_vr_pairing SET used_at = ?"
                        " WHERE code_hash = ? AND used_at IS NULL", (now, code_hash(code)))
        if cur.rowcount != 1:         # gleichzeitig schon eingelöst
            raise PairingError("code_invalid")
    return {"username": row["username"], "name": row["name"]}


def add_headset(user: str, name: str, key_id: str) -> dict:
    hid = secrets.token_hex(8)
    now = _now().isoformat()
    with db() as c:
        c.execute("INSERT INTO module_vr_headsets (id, username, name, key_id, paired_at)"
                  " VALUES (?, ?, ?, ?, ?)", (hid, user, name, key_id, now))
    return {"id": hid, "name": name, "paired_at": now}


def list_headsets(user: str) -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT id, name, paired_at FROM module_vr_headsets WHERE username = ?"
                         " ORDER BY paired_at DESC", (user,)).fetchall()
    return [dict(r) for r in rows]


def remove_headset(user: str, hid: str) -> str | None:
    """Entfernt die Brille von [user]; liefert ihre Key-ID (zum Widerrufen) oder None."""
    with db() as c:
        row = c.execute("SELECT key_id FROM module_vr_headsets WHERE id = ? AND username = ?",
                        (hid, user)).fetchone()
        if not row:
            return None
        c.execute("DELETE FROM module_vr_headsets WHERE id = ?", (hid,))
    return row["key_id"]
