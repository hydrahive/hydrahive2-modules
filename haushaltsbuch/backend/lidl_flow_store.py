"""DB-Rate-Limit und Einmalzustand für Lidl-PKCE-Flows."""
from __future__ import annotations

from datetime import datetime, timezone

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .access import membership
from .lidl_flow import AuthFlowError, flow_hash


def create_flow_record(
    principal: AuthPrincipal, flow_id: str, scope: str, expires_at: datetime,
) -> tuple[int, int]:
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        attempts = conn.execute(
            "SELECT COUNT(*) FROM module_haushaltsbuch_loyalty_auth_flows "
            "WHERE member_id=? AND julianday(created_at)>julianday('now','-10 minutes')",
            (member["id"],),
        ).fetchone()[0]
        if attempts >= 5:
            raise AuthFlowError("lidl_auth_rate_limited", 429)
        conn.execute(
            "DELETE FROM module_haushaltsbuch_loyalty_auth_flows "
            "WHERE julianday(expires_at)<=julianday('now')"
        )
        conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_auth_flows"
            "(flow_id_hash,household_id,member_id,scope,expires_at) VALUES(?,?,?,?,?)",
            (
                flow_hash(flow_id), member["household_id"], member["id"], scope,
                expires_at.isoformat(),
            ),
        )
    return member["household_id"], member["id"]


def claim_flow(flow: dict, principal: AuthPrincipal, scope: str) -> None:
    now = datetime.now(timezone.utc)
    try:
        expires = datetime.fromisoformat(flow["expires_at"])
    except (TypeError, ValueError) as exc:
        raise AuthFlowError("lidl_auth_flow_invalid") from exc
    with db(immediate=True) as conn:
        member = membership(conn, principal)
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_auth_flows WHERE flow_id_hash=?",
            (flow_hash(flow["flow_id"]),),
        ).fetchone()
        invalid_scope = (
            row is None or row["household_id"] != member["household_id"]
            or row["member_id"] != member["id"] or row["scope"] != scope
            or flow["household_id"] != member["household_id"]
            or flow["member_id"] != member["id"]
        )
        if invalid_scope:
            raise AuthFlowError("lidl_auth_flow_invalid")
        if row["consumed_at"] is not None:
            raise AuthFlowError("lidl_auth_flow_consumed", 409)
        if row["processing_at"] is not None:
            raise AuthFlowError("lidl_auth_flow_in_progress", 409)
        if row["attempt_count"] >= 3:
            raise AuthFlowError("lidl_auth_rate_limited", 429)
        if expires <= now or datetime.fromisoformat(row["expires_at"]) <= now:
            raise AuthFlowError("lidl_auth_flow_expired", 409)
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_auth_flows "
            "SET processing_at=?,attempt_count=attempt_count+1 "
            "WHERE id=? AND processing_at IS NULL AND consumed_at IS NULL",
            (now.isoformat(), row["id"]),
        )


def finish_flow(flow: dict, consumed: bool) -> None:
    with db(immediate=True) as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_auth_flows SET processing_at=NULL,"
            "consumed_at=CASE WHEN ? THEN ? ELSE consumed_at END WHERE flow_id_hash=?",
            (
                int(consumed), datetime.now(timezone.utc).isoformat(),
                flow_hash(flow["flow_id"]),
            ),
        )
