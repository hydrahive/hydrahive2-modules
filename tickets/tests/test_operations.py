from __future__ import annotations

import pytest

from hydrahive.api.middleware.auth import AuthPrincipal

from backend.dashboard import dashboard_summary
from backend.models import TicketCreate
from backend.service import create_ticket
from backend.views import create_view, delete_view, list_views


def principal(user_id: str = "user-member", role: str = "user") -> AuthPrincipal:
    return AuthPrincipal(user_id=user_id, username=user_id, role=role)


def test_dashboard_reports_due_and_assignment_counts(ticket_db):
    create_ticket(TicketCreate(title="Late", due_at="2020-01-01T00:00:00Z"), principal())
    create_ticket(TicketCreate(title="Unassigned"), principal("user-other"))

    summary = dashboard_summary(principal())

    assert summary["open"] == 2
    assert summary["overdue"] == 1
    assert summary["unassigned"] == 2
    assert summary["mine"] == 1


def test_saved_views_are_user_scoped_and_filters_are_declarative(ticket_db):
    view = create_view(
        principal(),
        name="Meine dringenden Tickets",
        filters={"priority": "urgent", "overdue": True},
        sort="due_at",
        direction="asc",
    )

    assert view["name"] == "Meine dringenden Tickets"
    assert list_views(principal())[0]["id"] == view["id"]
    assert list_views(principal("user-other")) == []
    delete_view(view["id"], principal())
    assert list_views(principal()) == []


def test_saved_view_rejects_unknown_filter_keys(ticket_db):
    with pytest.raises(ValueError, match="invalid_view_filter"):
        create_view(principal(), name="Bad", filters={"sql": "DROP TABLE"})
