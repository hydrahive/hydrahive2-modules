"""Einstellungen des Fernsehers (eine Zeile in module_fernseher_settings). Schlüssel nur verschlüsselt."""
from __future__ import annotations

from hydrahive.db.connection import db

from . import psk_crypto, validators

DEFAULT_LIMIT = 60
_EMPTY = {"configured": False, "name": "", "address": "", "psk_set": False, "volume_limit": DEFAULT_LIMIT}


def _row():
    with db() as conn:
        return conn.execute(
            "SELECT name, address, psk_sealed, volume_limit FROM module_fernseher_settings WHERE id = 1"
        ).fetchone()


def save(*, name: str, address: str, psk: str | None, volume_limit: int, user: str) -> dict:
    """Speichern. psk=None (oder leer) behält den bisherigen Schlüssel; beim ersten Speichern Pflicht."""
    addr = validators.normalize_address(address)
    if not isinstance(volume_limit, int) or not 1 <= volume_limit <= 100:
        raise ValueError("volume_limit muss zwischen 1 und 100 liegen")
    old = _row()
    if psk:
        sealed = psk_crypto.seal(psk)
    elif old is not None:
        sealed = old[2]
    else:
        raise ValueError("psk_missing")
    with db() as conn:
        conn.execute(
            "INSERT INTO module_fernseher_settings (id, name, address, psk_sealed, volume_limit, updated_by,"
            " updated_at) VALUES (1, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'))"
            " ON CONFLICT(id) DO UPDATE SET name = excluded.name, address = excluded.address,"
            " psk_sealed = excluded.psk_sealed, volume_limit = excluded.volume_limit,"
            " updated_by = excluded.updated_by, updated_at = excluded.updated_at",
            ((name or "").strip()[:80], addr, sealed, volume_limit, user),
        )
    return public()


def public() -> dict:
    row = _row()
    if row is None:
        return dict(_EMPTY)
    return {"configured": True, "name": row[0], "address": row[1], "psk_set": bool(row[2]),
            "volume_limit": int(row[3])}


def connection() -> tuple[str, str] | None:
    """(Adresse, Klartext-Schlüssel) für den Client – nur serverseitig benutzen."""
    row = _row()
    if row is None:
        return None
    return row[1], psk_crypto.open_(row[2])


def volume_limit() -> int:
    row = _row()
    return int(row[3]) if row is not None else DEFAULT_LIMIT
