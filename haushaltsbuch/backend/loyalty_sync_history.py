"""Haushaltsgebundene, redigierte Historie manueller Loyalty-Syncs."""
from __future__ import annotations

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .access import membership
from .loyalty_connections import _manageable


def list_sync_runs(connection_id: int, principal: AuthPrincipal) -> list[dict]:
    with db() as conn:
        member = membership(conn, principal)
        _manageable(conn, connection_id, member)
        rows = conn.execute(
            "SELECT * FROM module_haushaltsbuch_loyalty_sync_runs "
            "WHERE connection_id=? AND household_id=? ORDER BY id DESC LIMIT 100",
            (connection_id, member["household_id"]),
        ).fetchall()
    return [dict(row) for row in rows]
