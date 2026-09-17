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


def test_get_and_list_support_filters(ticket_db):
    create(TicketCreate(title="Login", priority="urgent", project_id="project-a"))
    create(TicketCreate(title="UI", priority="low", project_id="project-b"))

    ticket = get_ticket(list_tickets(priority="urgent")[0]["id"])
    matches = list_tickets(project_id="project-a", query="login")

    assert ticket["title"] == "Login"
    assert len(matches) == 1
    assert matches[0]["priority"] == "urgent"


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
