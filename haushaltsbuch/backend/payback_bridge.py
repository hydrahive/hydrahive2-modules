"""One-time-code lifecycle and transactional PAYBACK browser imports."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from fastapi import status
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db
from hydrahive.settings import settings

from . import audit
from .access import membership, require_row
from .loyalty_connections import _connection_dict
from .loyalty_persistence import persist_sync
from .payback_bridge_models import PaybackBridgeImport, PaybackBridgeStart
from .payback_normalize import sync_payload

FLOW_TTL = timedelta(minutes=10)
IMPORT_PATH = "/api/modules/haushaltsbuch/loyalty/payback/bridge/import"
_GENERIC_ERROR = "payback_bridge_import_invalid"
_CAPABILITIES = {
    "balance": True,
    "expirations": True,
    "activities": True,
    "coupons": True,
    "partners": True,
}


def _hmac(value: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def reject_invalid_import() -> None:
    raise coded(status.HTTP_404_NOT_FOUND, _GENERIC_ERROR)


def start_flow(body: PaybackBridgeStart, principal: AuthPrincipal) -> dict:
    now = datetime.now(timezone.utc)
    expires_at = now + FLOW_TTL
    pairing_code = secrets.token_urlsafe(32)  # 32 random bytes = 256 bits.
    flow_id = str(uuid.uuid4())
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        recent = conn.execute(
            "SELECT COUNT(*) FROM module_haushaltsbuch_payback_bridge_flows "
            "WHERE member_id=? AND julianday(created_at)>julianday(?,'-10 minutes')",
            (member["id"], now.isoformat()),
        ).fetchone()[0]
        if recent >= 5:
            raise coded(
                status.HTTP_429_TOO_MANY_REQUESTS, "payback_bridge_rate_limited"
            )
        conn.execute(
            "DELETE FROM module_haushaltsbuch_payback_bridge_flows "
            "WHERE consumed_at IS NULL AND julianday(expires_at)<=julianday(?,'-1 day')",
            (now.isoformat(),),
        )
        conn.execute(
            "INSERT INTO module_haushaltsbuch_payback_bridge_flows"
            "(flow_id,code_hmac,household_id,member_id,alias,visibility,expires_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                flow_id,
                _hmac(pairing_code),
                member["household_id"],
                member["id"],
                body.alias,
                body.visibility,
                expires_at.isoformat(),
            ),
        )
    return {
        "flow_id": flow_id,
        "pairing_code": pairing_code,
        "expires_at": expires_at.isoformat(),
        "import_path": IMPORT_PATH,
    }


def flow_status(flow_id: str, principal: AuthPrincipal) -> dict:
    now = datetime.now(timezone.utc)
    with db() as conn:
        member = membership(conn, principal)
        flow = require_row(
            conn.execute(
                "SELECT * FROM module_haushaltsbuch_payback_bridge_flows "
                "WHERE flow_id=? AND household_id=? AND member_id=?",
                (flow_id, member["household_id"], member["id"]),
            ).fetchone(),
            "payback_bridge_flow_not_found",
        )
        if flow["consumed_at"] is not None:
            state = "consumed"
        elif datetime.fromisoformat(flow["expires_at"]) <= now:
            state = "expired"
        else:
            state = "pending"
        result = {
            "flow_id": flow["flow_id"],
            "status": state,
            "expires_at": flow["expires_at"],
        }
        if flow["connection_id"] is not None:
            connection = conn.execute(
                "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
                (flow["connection_id"],),
            ).fetchone()
            if connection is not None:
                result["connection"] = _connection_dict(connection)
    return result


def _connection_for_flow(conn: sqlite3.Connection, flow: sqlite3.Row) -> sqlite3.Row:
    account_fingerprint = _hmac(
        f"payback-browser-bridge|{flow['household_id']}|{flow['member_id']}"
    )
    row = conn.execute(
        "SELECT * FROM module_haushaltsbuch_loyalty_connections "
        "WHERE household_id=? AND provider='payback' AND owner_member_id=? "
        "AND account_fingerprint=?",
        (flow["household_id"], flow["member_id"], account_fingerprint),
    ).fetchone()
    capabilities = json.dumps(_CAPABILITIES, separators=(",", ":"), sort_keys=True)
    if row is None:
        cursor = conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_connections"
            "(household_id,provider,owner_member_id,credential_ref,account_fingerprint,"
            "masked_account,alias,country_code,language_code,visibility,status,"
            "capabilities_json,feature_enabled,sync_enabled) "
            "VALUES(?,'payback',?,'payback-browser-bridge',?,'PAYBACK Browser-Bridge',"
            "?,'DE','de',?,'active',?,1,0)",
            (
                flow["household_id"],
                flow["member_id"],
                account_fingerprint,
                flow["alias"],
                flow["visibility"],
                capabilities,
            ),
        )
        connection_id = cursor.lastrowid
    else:
        connection_id = row["id"]
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections SET alias=?,visibility=?,"
            "status='active',capabilities_json=?,feature_enabled=1,sync_enabled=0,"
            "last_error_code=NULL,last_sync_at=?,last_success_at=?,revision=revision+1,"
            "updated_at=? WHERE id=?",
            (
                flow["alias"],
                flow["visibility"],
                capabilities,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                connection_id,
            ),
        )
    return conn.execute(
        "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
        (connection_id,),
    ).fetchone()


def import_payload(body: PaybackBridgeImport) -> dict:
    now = datetime.now(timezone.utc)
    digest = _hmac(body.pairing_code)
    with db(immediate=True) as conn:
        flow = conn.execute(
            "SELECT * FROM module_haushaltsbuch_payback_bridge_flows "
            "WHERE code_hmac=? AND consumed_at IS NULL "
            "AND julianday(expires_at)>julianday(?)",
            (digest, now.isoformat()),
        ).fetchone()
        if flow is None:
            reject_invalid_import()
        connection = _connection_for_flow(conn, flow)
        counts = persist_sync(conn, connection, sync_payload(body))
        updated = conn.execute(
            "UPDATE module_haushaltsbuch_payback_bridge_flows "
            "SET consumed_at=?,connection_id=? "
            "WHERE id=? AND consumed_at IS NULL AND julianday(expires_at)>julianday(?)",
            (now.isoformat(), connection["id"], flow["id"], now.isoformat()),
        )
        if updated.rowcount != 1:
            reject_invalid_import()
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections SET last_sync_at=?,"
            "last_success_at=?,updated_at=? WHERE id=?",
            (now.isoformat(), now.isoformat(), now.isoformat(), connection["id"]),
        )
        actor = conn.execute(
            "SELECT user_id FROM module_haushaltsbuch_members WHERE id=?",
            (flow["member_id"],),
        ).fetchone()
        audit.record(
            conn,
            flow["household_id"],
            actor["user_id"] if actor else "payback-bridge",
            "loyalty_connection",
            connection["id"],
            "browser_import",
            after={"counts": asdict(counts)},
        )
        connection = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (connection["id"],),
        ).fetchone()
    return {"imported": True, "counts": asdict(counts)}
