"""HydraHive-App (G1): Kopplungs-Codes und App-Geräte. Muster: Modul mining (pairing.py, rigs.py).

Code: 12 Zeichen ohne Verwechsler (kein 0/O, 1/I/L), 15 min gültig, einmalig, nur als SHA-256 gespeichert. Zusammen
mit dem Rate-Limit des Kerns (240/min je IP) nicht durchprobierbar. Beim Koppeln tauscht die App den Code gegen einen
eigenen Schlüssel `hhtvw_…`; gespeichert wird auch der nur als SHA-256. Name und Zuordnung kommen vom Code (vom
Admin), nicht von der App. Sperren löscht den Schlüssel.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 12
TTL_MINUTES = 15
TOKEN_PREFIX = "hhtvw_"
NAME_MAX = 40
_INFO = {"kind": 10, "model": 80, "android": 20, "app_version": 30}
_PUBLIC = ("app_id", "name", "device_id", "kind", "model", "android", "app_version", "status", "remote_ip",
           "created_at", "last_seen")


class AppError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize(code: str) -> str:
    return re.sub(r"[\s-]", "", str(code or "")).upper()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def clean_name(name: str) -> str:
    raw = str(name or "")
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise AppError("tvw_app_bad_name")
    n = " ".join(raw.split())
    if not n or len(n) > NAME_MAX:
        raise AppError("tvw_app_bad_name")
    return n


def create_code(name: str, device_id: str, created_by: str) -> dict:
    """Neuen Code anlegen. Der Klartext kommt genau einmal zurück."""
    n = clean_name(name)
    with db() as conn:
        if conn.execute("SELECT 1 FROM module_tvwerkstatt_app_devices WHERE name = ? AND status = 'active'",
                        (n,)).fetchone():
            raise AppError("tvw_app_name_taken")
        if device_id and not conn.execute("SELECT 1 FROM module_tvwerkstatt_devices WHERE device_id = ?",
                                          (device_id,)).fetchone():
            raise AppError("tvw_device_not_found")
        raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
        expires = _iso(_now() + timedelta(minutes=TTL_MINUTES))
        conn.execute("INSERT INTO module_tvwerkstatt_app_pairing (code_hash, name, device_id, expires_at, created_by) "
                     "VALUES (?, ?, ?, ?, ?)", (_sha(raw), n, device_id or "", expires, created_by))
        conn.commit()
    return {"code": "-".join(raw[i:i + 4] for i in range(0, CODE_LEN, 4)), "name": n, "expires_at": expires}


def code_valid(code: str) -> bool:
    c = normalize(code)
    if len(c) != CODE_LEN:
        return False
    with db() as conn:
        return conn.execute("SELECT 1 FROM module_tvwerkstatt_app_pairing WHERE code_hash = ? AND used_at IS NULL "
                            "AND expires_at > ?", (_sha(c), _iso(_now()))).fetchone() is not None


def _info(info: dict) -> dict:
    out = {}
    for k, limit in _INFO.items():
        v = info.get(k) if isinstance(info, dict) else None
        if isinstance(v, (str, int)) and not isinstance(v, bool):
            s = " ".join(str(v).split())[:limit]
            if all(32 <= ord(ch) != 127 for ch in s):
                out[k] = s
    if out.get("kind") not in (None, "tv", "tablet"):
        out["kind"] = ""
    return out


def enroll(code: str, info: dict, remote_ip: str) -> dict:
    """Code gegen Schlüssel tauschen – einmalig, atomar (zwei Geräte können denselben Code nicht beide nutzen)."""
    hashed = _sha(normalize(code))
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    app_id = uuid.uuid4().hex[:16]
    meta = _info(info)
    now = _iso(_now())
    with db(immediate=True) as conn:                    # Schreibsperre vorab; Fehler rollen alles zurück
        row = conn.execute("SELECT name, device_id FROM module_tvwerkstatt_app_pairing WHERE code_hash = ? "
                           "AND used_at IS NULL AND expires_at > ?", (hashed, now)).fetchone()
        if row is None:
            raise AppError("tvw_app_code_invalid")
        name, device_id = row[0], row[1]
        if conn.execute("SELECT 1 FROM module_tvwerkstatt_app_devices WHERE name = ? AND status = 'active'",
                        (name,)).fetchone():
            raise AppError("tvw_app_name_taken")
        conn.execute("DELETE FROM module_tvwerkstatt_app_devices WHERE name = ? AND status = 'revoked'", (name,))
        conn.execute("UPDATE module_tvwerkstatt_app_pairing SET used_at = ? WHERE code_hash = ?", (now, hashed))
        conn.execute("INSERT INTO module_tvwerkstatt_app_devices (app_id, name, device_id, kind, model, android, "
                     "app_version, token_hash, remote_ip, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (app_id, name, device_id, meta.get("kind", ""), meta.get("model", ""), meta.get("android", ""),
                      meta.get("app_version", ""), _sha(token), str(remote_ip or "")[:64], now))
    return {"app_id": app_id, "name": name, "token": token}


def by_token(token: str) -> dict | None:
    if not token or not token.startswith(TOKEN_PREFIX) or len(token) > 100:
        return None
    with db() as conn:
        r = conn.execute(f"SELECT {', '.join(_PUBLIC)} FROM module_tvwerkstatt_app_devices "
                         "WHERE token_hash = ? AND status = 'active'", (_sha(token),)).fetchone()
    return dict(zip(_PUBLIC, r, strict=True)) if r else None


def seen(app_id: str, remote_ip: str, state: dict | None = None) -> None:
    raw = json.dumps(state or {}, separators=(",", ":"))[:4000] if state is not None else None
    with db() as conn:
        if raw is None:
            conn.execute("UPDATE module_tvwerkstatt_app_devices SET last_seen = ?, remote_ip = ? WHERE app_id = ?",
                         (_iso(_now()), str(remote_ip or "")[:64], app_id))
        else:
            conn.execute("UPDATE module_tvwerkstatt_app_devices SET last_seen = ?, remote_ip = ?, state = ? "
                         "WHERE app_id = ?", (_iso(_now()), str(remote_ip or "")[:64], raw, app_id))
        conn.commit()


def all_devices() -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(_PUBLIC)}, state FROM module_tvwerkstatt_app_devices "
                            "ORDER BY created_at, name").fetchall()
    out = []
    for r in rows:
        d = dict(zip((*_PUBLIC, "state"), r, strict=True))
        try:
            d["state"] = json.loads(d["state"] or "{}")
        except ValueError:
            d["state"] = {}
        out.append(d)
    return out


def revoke(app_id: str) -> None:
    with db() as conn:
        cur = conn.execute("UPDATE module_tvwerkstatt_app_devices SET status = 'revoked', token_hash = NULL "
                           "WHERE app_id = ?", (app_id,))
        conn.commit()
    if cur.rowcount != 1:
        raise AppError("tvw_app_not_found")


def remove(app_id: str) -> None:
    with db() as conn:
        cur = conn.execute("DELETE FROM module_tvwerkstatt_app_devices WHERE app_id = ? AND status = 'revoked'",
                           (app_id,))
        conn.commit()
    if cur.rowcount != 1:
        raise AppError("tvw_app_not_revoked")
