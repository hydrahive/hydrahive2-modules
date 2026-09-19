from __future__ import annotations

import pytest

from hydrahive.api.middleware.auth import AuthPrincipal

from backend.models import TicketCommentCreate, TicketCreate, TicketUpdate
from backend.service import (
    TicketServiceError,
    add_comment,
    create_ticket,
    get_ticket,
    list_comments,
    list_events,
    list_tickets,
    update_ticket,
)


def principal(user_id: str = "user-1") -> AuthPrincipal:
    return AuthPrincipal(user_id=user_id, username=user_id, role="user")


def create(body: TicketCreate | None = None) -> dict:
    return create_ticket(body or TicketCreate(title="Fehler im Dashboard"), principal())


def test_create_assigns_number_and_normalizes_tags(ticket_db):
    first = create(TicketCreate(title=" Fehler im Dashboard ", tags=["bug", "ui"]))
    second = create(TicketCreate(title="Zweiter Vorgang"))

    assert first["number"] == 1
    assert second["number"] == 2
    assert first["title"] == "Fehler im Dashboard"
    assert first["status"] == "open"
    assert first["tags"] == ["bug", "ui"]


def test_create_calculates_sla_deadlines_and_manual_override(ticket_db):
    ticket = create(TicketCreate(title="Dringend", priority="urgent"))
    manual = create(TicketCreate(title="Manuell", due_at="2030-01-01T00:00:00Z"))

    assert ticket["response_due_at"]
    assert ticket["resolution_due_at"]
    assert ticket["due_at"] == ticket["resolution_due_at"]
    assert ticket["due_at_source"] == "sla"
    assert manual["due_at"] == "2030-01-01T00:00:00Z"
    assert manual["due_at_source"] == "manual"


def test_get_and_list_support_filters(ticket_db):
    create(TicketCreate(title="Login", priority="urgent", project_id="project-a"))
    create(TicketCreate(title="UI", priority="low", project_id="project-b"))

    ticket = get_ticket(list_tickets(priority="urgent")[0]["id"])
    matches = list_tickets(project_id="project-a", query="login")

    assert ticket["title"] == "Login"
    assert len(matches) == 1
    assert matches[0]["priority"] == "urgent"


def test_due_filters_and_sort_are_whitelisted(ticket_db):
    overdue = create(TicketCreate(title="Overdue", due_at="2020-01-01T00:00:00Z"))
    create(TicketCreate(title="Future", due_at="2030-01-01T00:00:00Z"))

    assert [item["id"] for item in list_tickets(overdue=True)] == [overdue["id"]]
    assert list_tickets(due_before="2021-01-01T00:00:00Z")[0]["id"] == overdue["id"]
    assert list_tickets(sort="due_at", direction="asc")[0]["id"] == overdue["id"]


def test_manual_due_date_can_be_reset_to_sla(ticket_db):
    ticket = create(TicketCreate(title="Fälligkeit"))
    overridden = update_ticket(ticket["id"], TicketUpdate(due_at="2030-01-01T00:00:00Z"), principal())
    reset = update_ticket(ticket["id"], TicketUpdate(due_at=None), principal())

    assert overridden["due_at_source"] == "manual"
    assert reset["due_at_source"] == "sla"
    assert reset["due_at"] == reset["resolution_due_at"]


def test_status_workflow_rejects_invalid_transition(ticket_db):
    ticket = create()
    updated = update_ticket(ticket["id"], TicketUpdate(status="triaged"), principal())
    assert updated["status"] == "triaged"

    with pytest.raises(TicketServiceError, match="invalid_status_transition"):
        update_ticket(ticket["id"], TicketUpdate(status="closed"), principal())


def test_resolution_timestamps_and_reopen(ticket_db):
    ticket = create()
    update_ticket(ticket["id"], TicketUpdate(status="in_progress"), principal())
    resolved = update_ticket(ticket["id"], TicketUpdate(status="resolved"), principal())
    reopened = update_ticket(ticket["id"], TicketUpdate(status="in_progress"), principal())

    assert resolved["resolved_at"]
    assert reopened["resolved_at"] is None


def test_update_is_audited_without_secret_payloads(ticket_db):
    ticket = create()
    update_ticket(ticket["id"], TicketUpdate(priority="high", tags=["ops"]), principal())
    events = list_events(ticket["id"])

    assert [event["event_type"] for event in events] == ["ticket_created", "ticket_updated"]
    assert events[-1]["payload"] == {"priority": "high", "tags": ["ops"]}


def test_comments_are_append_only_and_audited(ticket_db):
    ticket = create()
    body = TicketCommentCreate(body="Bitte Logs prüfen.")
    comment = add_comment(ticket["id"], body.body, principal())

    assert comment["body"] == body.body
    assert [item["body"] for item in list_comments(ticket["id"])] == [body.body]
    assert list_events(ticket["id"])[-1]["event_type"] == "comment_added"


def test_missing_ticket_is_domain_error(ticket_db):
    with pytest.raises(TicketServiceError, match="ticket_not_found"):
        add_comment("missing", "Kommentar", principal())


def test_invalid_input_is_rejected_by_models():
    with pytest.raises(ValueError):
        TicketCreate(title="   ")
    with pytest.raises(ValueError):
        TicketCommentCreate(body="\n")
