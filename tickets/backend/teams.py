"""Team CRUD used by the internal ticket assignment workflow."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.api.middleware.users import get_by_id
from hydrahive.db.connection import db

from .models import TeamCreate, TeamMemberUpsert, TeamUpdate
from .service import TicketServiceError


def _team(conn: sqlite3.Connection, team_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM module_ticket_teams WHERE id=?", (team_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["members"] = [
        dict(member)
        for member in conn.execute(
            "SELECT team_id,user_id,role,created_at FROM module_ticket_team_members "
            "WHERE team_id=? ORDER BY role DESC,user_id", (team_id,)
        ).fetchall()
    ]
    return result


def list_teams() -> list[dict]:
    with db() as conn:
        ids = [row["id"] for row in conn.execute("SELECT id FROM module_ticket_teams ORDER BY name").fetchall()]
        return [_team(conn, team_id) for team_id in ids]  # type: ignore[misc]


def create_team(body: TeamCreate, principal: AuthPrincipal) -> dict:
    team_id = str(uuid4())
    with db(immediate=True) as conn:
        try:
            conn.execute(
                "INSERT INTO module_ticket_teams(id,name,description,created_by) VALUES(?,?,?,?)",
                (team_id, body.name, body.description, principal.user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise TicketServiceError("team_name_taken") from exc
        result = _team(conn, team_id)
    return result  # type: ignore[return-value]


def update_team(team_id: str, body: TeamUpdate) -> dict:
    changes = body.model_dump(exclude_unset=True)
    with db(immediate=True) as conn:
        if _team(conn, team_id) is None:
            raise TicketServiceError("team_not_found")
        if changes:
            assignments = [f"{key}=?" for key in changes]
            args = [changes[key] for key in changes]
            assignments.append("updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')")
            args.append(team_id)
            try:
                conn.execute(f"UPDATE module_ticket_teams SET {','.join(assignments)} WHERE id=?", args)
            except sqlite3.IntegrityError as exc:
                raise TicketServiceError("team_name_taken") from exc
        return _team(conn, team_id)  # type: ignore[return-value]


def add_member(team_id: str, body: TeamMemberUpsert) -> dict:
    if get_by_id(body.user_id) is None:
        raise TicketServiceError("user_not_found")
    with db(immediate=True) as conn:
        if _team(conn, team_id) is None:
            raise TicketServiceError("team_not_found")
        conn.execute(
            "INSERT INTO module_ticket_team_members(team_id,user_id,role) VALUES(?,?,?) "
            "ON CONFLICT(team_id,user_id) DO UPDATE SET role=excluded.role",
            (team_id, body.user_id, body.role),
        )
        row = conn.execute(
            "SELECT team_id,user_id,role,created_at FROM module_ticket_team_members WHERE team_id=? AND user_id=?",
            (team_id, body.user_id),
        ).fetchone()
    return dict(row)


def remove_member(team_id: str, user_id: str) -> bool:
    with db(immediate=True) as conn:
        cursor = conn.execute(
            "DELETE FROM module_ticket_team_members WHERE team_id=? AND user_id=?",
            (team_id, user_id),
        )
    return cursor.rowcount > 0
