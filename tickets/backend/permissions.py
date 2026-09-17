"""Permission predicates for internal ticket and team operations."""
from __future__ import annotations

import sqlite3

from hydrahive.api.middleware.auth import AuthPrincipal

_ADMIN_ROLES = {"admin", "system_admin"}


def is_admin(principal: AuthPrincipal) -> bool:
    return principal.role in _ADMIN_ROLES


def can_read_ticket(principal: AuthPrincipal) -> bool:
    """All authenticated users may read internal tickets in V1."""
    return bool(principal.user_id)


def can_comment_ticket(principal: AuthPrincipal) -> bool:
    """All authenticated users may add internal comments in V1."""
    return bool(principal.user_id)


def is_team_member(
    conn: sqlite3.Connection, team_id: str | None, user_id: str, *, lead_only: bool = False
) -> bool:
    if not team_id:
        return False
    query = "SELECT role FROM module_ticket_team_members WHERE team_id=? AND user_id=?"
    row = conn.execute(query, (team_id, user_id)).fetchone()
    return row is not None and (not lead_only or row["role"] == "lead")


def can_update_ticket(
    conn: sqlite3.Connection, ticket: sqlite3.Row, principal: AuthPrincipal
) -> bool:
    if is_admin(principal):
        return True
    if ticket["created_by"] == principal.user_id or ticket["assigned_to"] == principal.user_id:
        return True
    return is_team_member(conn, ticket["team_id"], principal.user_id)


def can_manage_team(
    conn: sqlite3.Connection, team_id: str | None, principal: AuthPrincipal
) -> bool:
    return is_admin(principal) or is_team_member(conn, team_id, principal.user_id, lead_only=True)


def can_create_team(principal: AuthPrincipal) -> bool:
    return is_admin(principal)
