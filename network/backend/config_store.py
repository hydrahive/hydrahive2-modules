"""Einrichtung (genau eine): Adressen, NAMEN der Safe-Einträge (nie Geheimnisse), bestätigter Fingerabdruck, Tarif,
letzter Status der Dream Machine."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from hydrahive.db.connection import db

CONFIG_ID = "main"
EDIT = ("udm_url", "udm_credential", "fritz_host", "fritz_credential", "plan_down_mbit", "plan_up_mbit",
        "plan_price_eur")
_COLS = ("owner", *EDIT, "udm_pin", "last_full_sync", "last_status", "last_status_at", "last_error", "updated_at")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get() -> dict | None:
    with db() as conn:
        r = conn.execute(f"SELECT {', '.join(_COLS)} FROM module_network_config WHERE config_id = ?",
                         (CONFIG_ID,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["last_status"] = json.loads(d["last_status"]) if d["last_status"] else None
    return d


def save(*, owner: str, **values) -> dict:
    """Einstellungen speichern. Ändert sich die Adresse der Dream Machine, gilt die Bestätigung nicht mehr."""
    old = get()
    pin = old["udm_pin"] if old and old["udm_url"] == values.get("udm_url") else None
    row = {k: values.get(k) for k in EDIT}
    cols = ("config_id", "owner", *EDIT, "udm_pin", "updated_at")
    args = (CONFIG_ID, owner, *row.values(), pin, _now())
    upd = ", ".join(f"{c} = excluded.{c}" for c in cols[1:])
    with db() as conn:
        conn.execute(f"INSERT INTO module_network_config ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
                     f"ON CONFLICT(config_id) DO UPDATE SET {upd}", args)
    return get() or {}


def set_pin(pin: str | None) -> None:
    with db() as conn:
        conn.execute("UPDATE module_network_config SET udm_pin = ?, updated_at = ? WHERE config_id = ?",
                     (pin, _now(), CONFIG_ID))


def set_status(*, status: dict | None, at: int, error: str | None) -> None:
    sets, args = ["last_error = ?"], [error]
    if status is not None:
        sets += ["last_status = ?", "last_status_at = ?"]
        args += [json.dumps(status), at]
    with db() as conn:
        conn.execute(f"UPDATE module_network_config SET {', '.join(sets)} WHERE config_id = ?", (*args, CONFIG_ID))


def set_full_sync(at: int) -> None:
    with db() as conn:
        conn.execute("UPDATE module_network_config SET last_full_sync = ? WHERE config_id = ?", (at, CONFIG_ID))
