"""Sichere Verwaltung providerneutraler Kundenkarten-Verbindungen."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.credentials.store import delete_credential, get_credential
from hydrahive.db.connection import db
from hydrahive.settings import settings

from . import audit
from .access import conflict, membership, require_row
from .common import NOW
from .loyalty_requests import LoyaltyConnectionCreate, LoyaltyConnectionUpdate


def _fingerprint(household_id: int, provider: str, account_id: str) -> str:
    message = f"{household_id}|{provider}|{account_id}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


def _connection_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result.pop("account_fingerprint", None)
    result.pop("credential_ref", None)
    result["capabilities"] = json.loads(result.pop("capabilities_json"))
    result["feature_enabled"] = bool(result["feature_enabled"])
    result["sync_enabled"] = bool(result["sync_enabled"])
    return result


def _visible_sql(member: sqlite3.Row) -> tuple[str, list]:
    if member["role"] == "owner":
        return "household_id=?", [member["household_id"]]
    return (
        "household_id=? AND (owner_member_id=? OR visibility='household')",
        [member["household_id"], member["id"]],
    )


def _manageable(conn: sqlite3.Connection, connection_id: int, member: sqlite3.Row) -> sqlite3.Row:
    row = require_row(
        conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections "
            "WHERE id=? AND household_id=?",
            (connection_id, member["household_id"]),
        ).fetchone(),
        "loyalty_connection_not_found",
    )
    if member["role"] != "owner" and row["owner_member_id"] != member["id"]:
        return require_row(None, "loyalty_connection_not_found")
    return row


def list_connections(principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        where, params = _visible_sql(member)
        rows = conn.execute(
            f"SELECT * FROM module_haushaltsbuch_loyalty_connections "
            f"WHERE {where} ORDER BY provider,alias,id",
            params,
        ).fetchall()
    return [_connection_dict(row) for row in rows]


def create_connection(body: LoyaltyConnectionCreate, principal: AuthPrincipal) -> dict:
    # Existence only: credential values never enter module persistence or audit.
    if get_credential(principal.username, body.credential_ref) is None:
        return require_row(None, "credential_not_found")
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        fingerprint = _fingerprint(
            member["household_id"], body.provider, body.provider_account_id
        )
        try:
            cursor = conn.execute(
                "INSERT INTO module_haushaltsbuch_loyalty_connections"
                "(household_id,provider,owner_member_id,credential_ref,account_fingerprint,"
                "masked_account,alias,country_code,language_code,visibility,status) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,'active')",
                (
                    member["household_id"], body.provider, member["id"],
                    body.credential_ref, fingerprint, body.masked_account, body.alias,
                    body.country_code, body.language_code, body.visibility,
                ),
            )
        except sqlite3.IntegrityError as exc:
            from fastapi import status
            from hydrahive.api.middleware.errors import coded

            raise coded(status.HTTP_409_CONFLICT, "loyalty_connection_exists") from exc
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (cursor.lastrowid,),
        ).fetchone()
        audit.record(
            conn, member["household_id"], principal.user_id,
            "loyalty_connection", row["id"], "create",
            after={"provider": row["provider"], "visibility": row["visibility"]},
        )
    return _connection_dict(row)


def enable_experimental(connection_id: int, principal: AuthPrincipal) -> dict:
    """Aktiviert genau die soeben vom Mitglied erstellte Opt-in-Verbindung."""
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        row = _manageable(conn, connection_id, member)
        conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_connections SET feature_enabled=1,"
            f"status='active',revision=revision+1,updated_at={NOW} WHERE id=?",
            (connection_id,),
        )
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (row["id"],),
        ).fetchone()
    return _connection_dict(row)


def update_connection(
    connection_id: int, body: LoyaltyConnectionUpdate, principal: AuthPrincipal
) -> dict:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        before = _manageable(conn, connection_id, member)
        cursor = conn.execute(
            f"UPDATE module_haushaltsbuch_loyalty_connections "
            f"SET alias=?,visibility=?,revision=revision+1,updated_at={NOW} "
            "WHERE id=? AND household_id=? AND revision=?",
            (
                body.alias, body.visibility, connection_id,
                member["household_id"], body.revision,
            ),
        )
        if not cursor.rowcount:
            conflict()
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (connection_id,),
        ).fetchone()
        audit.record(
            conn, member["household_id"], principal.user_id,
            "loyalty_connection", connection_id, "update",
            before={"alias": before["alias"], "visibility": before["visibility"]},
            after={"alias": row["alias"], "visibility": row["visibility"]},
        )
    return _connection_dict(row)


def delete_connection(
    connection_id: int, revision: int, principal: AuthPrincipal
) -> None:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        row = _manageable(conn, connection_id, member)
        if row["revision"] != revision:
            conflict()
        audit.record(
            conn, member["household_id"], principal.user_id,
            "loyalty_connection", connection_id, "delete",
            before={"provider": row["provider"], "masked_account": row["masked_account"]},
        )
        owner = conn.execute(
            "SELECT username FROM module_haushaltsbuch_members WHERE id=?",
            (row["owner_member_id"],),
        ).fetchone()
        managed_ref = (
            row["provider"] == "lidl_plus"
            and row["credential_ref"].startswith(f"lidl-{row['owner_member_id']}-")
        )
        credential_ref = row["credential_ref"]
        conn.execute(
            "DELETE FROM module_haushaltsbuch_loyalty_connections "
            "WHERE id=? AND household_id=?",
            (connection_id, member["household_id"]),
        )
    if managed_ref and owner is not None:
        delete_credential(owner["username"], credential_ref)
