from __future__ import annotations

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from backend.models import TicketCreate
from backend.permissions import (
    can_comment_ticket,
    can_create_team,
    can_manage_team,
    can_read_ticket,
    can_update_ticket,
)
from backend.service import create_ticket


def p(user_id: str, role: str = "user") -> AuthPrincipal:
    return AuthPrincipal(user_id=user_id, username=user_id, role=role)


def test_all_authenticated_users_can_read_and_comment(ticket_db):
    assert can_read_ticket(p("outsider"))
    assert can_comment_ticket(p("outsider"))
    assert not can_read_ticket(AuthPrincipal("", "", "user"))


def test_creator_assignee_and_team_member_can_update(ticket_db):
    with db() as conn:
        conn.execute(
            "INSERT INTO module_ticket_teams(id,name,created_by) VALUES(?,?,?)",
            ("team-1", "Operations", "admin"),
        )
        conn.execute(
            "INSERT INTO module_ticket_team_members(team_id,user_id,role) VALUES(?,?,?)",
            ("team-1", "team-member", "member"),
        )
    ticket = create_ticket(
        TicketCreate(title="Teamfehler", assigned_to="assignee", team_id="team-1"),
        p("creator"),
    )
    with db() as conn:
        row = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket["id"],)).fetchone()

        assert can_update_ticket(conn, row, p("creator"))
        assert can_update_ticket(conn, row, p("assignee"))
        assert can_update_ticket(conn, row, p("team-member"))
        assert not can_update_ticket(conn, row, p("outsider"))


def test_admin_can_manage_all_teams_and_create_teams(ticket_db):
    admin = p("admin", "admin")
    assert can_create_team(admin)
    assert can_manage_team(None, "missing", admin)


def test_team_lead_can_manage_own_team_only(ticket_db):
    with db() as conn:
        conn.execute(
            "INSERT INTO module_ticket_teams(id,name,created_by) VALUES(?,?,?)",
            ("team-1", "Operations", "admin"),
        )
        conn.execute(
            "INSERT INTO module_ticket_team_members(team_id,user_id,role) VALUES(?,?,?)",
            ("team-1", "lead", "lead"),
        )
        assert can_manage_team(conn, "team-1", p("lead"))
        assert not can_manage_team(conn, "team-2", p("lead"))
        assert not can_create_team(p("lead"))
