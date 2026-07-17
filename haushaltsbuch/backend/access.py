from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded

Principal = Annotated[AuthPrincipal, Depends(require_principal)]


def membership(conn: sqlite3.Connection, principal: AuthPrincipal) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM module_haushaltsbuch_members WHERE user_id = ?",
        (principal.user_id,),
    ).fetchone()
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "household_not_found")
    return row


def owner_membership(conn: sqlite3.Connection, principal: AuthPrincipal) -> sqlite3.Row:
    row = membership(conn, principal)
    if row["role"] != "owner":
        raise coded(status.HTTP_403_FORBIDDEN, "owner_only")
    return row


def require_row(row: sqlite3.Row | None, code: str) -> sqlite3.Row:
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, code)
    return row


def conflict(code: str = "revision_conflict") -> None:
    raise coded(status.HTTP_409_CONFLICT, code)
