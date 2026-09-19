from __future__ import annotations

import pytest

from hydrahive.api.middleware.auth import AuthPrincipal

from backend.bulk import update_tickets
from backend.dashboard import dashboard_summary
from backend.models import SavedViewUpdate, SlaProfileCreate, SlaProfileUpdate, TicketCreate, TicketUpdate
from backend import sla_profiles
from backend.service import create_ticket
from backend.views import create_view, delete_view, list_views, update_view


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
    updated = update_view(view["id"], SavedViewUpdate(name="Updated", direction="desc"), principal())
    assert updated["name"] == "Updated"
    delete_view(view["id"], principal())
    assert list_views(principal()) == []


def test_saved_view_rejects_unknown_filter_keys(ticket_db):
    with pytest.raises(ValueError, match="invalid_view_filter"):
        create_view(principal(), name="Bad", filters={"sql": "DROP TABLE"})


def test_sla_profiles_are_admin_managed(ticket_db):
    created = sla_profiles.create_profile(SlaProfileCreate(name="Night shift", normal_resolution_hours=48))
    updated = sla_profiles.update_profile(created["id"], SlaProfileUpdate(active=False))

    assert updated["normal_resolution_hours"] == 48
    assert updated["active"] == 0
    assert any(item["id"] == "default" for item in sla_profiles.list_profiles())


def test_bulk_update_checks_each_ticket_and_audits_success(ticket_db):
    own = create_ticket(TicketCreate(title="Own"), principal())
    other = create_ticket(TicketCreate(title="Other"), principal("user-other"))

    result = update_tickets(
        principal(),
        [own["id"], other["id"], "missing"],
        TicketUpdate(priority="high"),
    )

    assert result["updated"] == 1
    assert result["skipped"] == 1
    assert result["failed"] == 1
    assert {item["status"] for item in result["results"]} == {"updated", "skipped", "error"}
