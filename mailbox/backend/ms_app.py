"""Die Microsoft-App von HydraHive (PLAN-M1b): einmal global vom Admin eingetragen, alle Nutzer melden sich
darüber an.

Client-ID = „Anwendungs-ID (Client)“ aus der App-Registrierung bei Microsoft (GUID). Kein Geheimnis
(öffentlicher Client, Geräte-Code). Verzeichnis (tenant): common (privat + Firma), consumers, organizations,
eine Tenant-GUID oder eine Domain.
"""
from __future__ import annotations

import re

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_NAMED = {"common", "consumers", "organizations"}
_KEYS = ("ms_client_id", "ms_tenant")


def normalize(client_id: str, tenant: str) -> tuple[str, str]:
    """Prüft und vereinheitlicht. Leere Client-ID ist nur über save('') erlaubt (= ausschalten)."""
    cid = (client_id or "").strip().lower()
    if not _GUID.match(cid):
        raise ValueError("Client-ID: bitte die „Anwendungs-ID (Client)“ eintragen (Form 1234abcd-…)")
    t = (tenant or "").strip().lower() or "common"
    if t not in _NAMED and not _GUID.match(t) and not _DOMAIN.match(t):
        raise ValueError("Verzeichnis: common, consumers, organizations, eine Tenant-ID oder eine Domain")
    return cid, t


def get() -> dict:
    with db() as c:
        q = f"SELECT key, value FROM module_mailbox_settings WHERE key IN ({','.join('?' * len(_KEYS))})"
        rows = dict(c.execute(q, _KEYS).fetchall())
    return {"client_id": rows.get("ms_client_id", ""), "tenant": rows.get("ms_tenant", "") or "common"}


def configured() -> bool:
    return bool(get()["client_id"])


def save(client_id: str, tenant: str) -> dict:
    if (client_id or "").strip():
        cid, t = normalize(client_id, tenant)
    else:
        cid, t = "", "common"
    now = now_iso()
    with db() as c:
        for k, v in (("ms_client_id", cid), ("ms_tenant", t)):
            c.execute("INSERT INTO module_mailbox_settings(key, value, updated_at) VALUES (?,?,?) ON CONFLICT(key) "
                      "DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, v, now))
    return get()
