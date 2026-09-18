from __future__ import annotations

from hydrahive.api.middleware.auth import AuthPrincipal

from backend.models import TicketCreate
from backend.notifications import list_for_user, mark_read
from backend.service import add_comment, create_ticket


def principal(user_id: str, username: str | None = None) -> AuthPrincipal:
    return AuthPrincipal(user_id, username or user_id, "user")


def test_assignment_creates_internal_notification(ticket_db):
    ticket = create_ticket(
        TicketCreate(title="Zuweisung", assigned_to="user-other"),
        principal("user-member", "member"),
    )

    assigned = list_for_user("user-other")
    creator = list_for_user("user-member")

    assert len(assigned) == 1
    assert assigned[0]["ticket_id"] == ticket["id"]
    assert assigned[0]["kind"] == "ticket_created"
    assert creator == []


def test_comment_notifies_creator_and_can_be_marked_read(ticket_db):
    ticket = create_ticket(TicketCreate(title="Verlauf"), principal("user-member", "member"))
    add_comment(ticket["id"], "Agentenhinweis", principal("user-other", "other"))
    items = list_for_user("user-member")
    assert items[-1]["kind"] == "comment_added"

    assert mark_read("user-member", items[-1]["id"])
    assert list_for_user("user-member") == []
    assert not mark_read("user-member", items[-1]["id"])
