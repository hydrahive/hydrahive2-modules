from __future__ import annotations

import pytest

from hydrahive.api.middleware.auth import AuthPrincipal
from backend.github import (
    GitHubConnectionCreate,
    GitHubLinkCreate,
    create_connection,
    create_link,
    get_link,
    list_connections,
    redact_connection,
    link_ticket,
    unlink_ticket,
)


def principal(user_id: str = "user-member") -> AuthPrincipal:
    return AuthPrincipal(user_id, "member", "user")


def test_connection_stores_only_credential_reference(ticket_db):
    connection = create_connection(
        GitHubConnectionCreate(
            project_id="project-1",
            owner="gh0stOo",
            repository="flowki-studio",
            project_number=1,
            credential_name="flowki-github",
        ),
        principal(),
    )
    assert connection["credential_name"] == "flowki-github"
    assert "credential_value" not in connection
    assert list_connections("project-1")[0]["owner"] == "gh0stOo"
    assert redact_connection(connection) == connection


def test_duplicate_connection_is_rejected(ticket_db):
    body = GitHubConnectionCreate(
        project_id="project-1", owner="owner", repository="repo", credential_name="github"
    )
    create_connection(body, principal())
    with pytest.raises(ValueError, match="github_connection_exists"):
        create_connection(body, principal())


def test_link_requires_existing_ticket_and_connection(ticket_db):
    body = GitHubLinkCreate(
        ticket_id="missing", connection_id="missing", owner="owner", repository="repo",
        issue_number=1, issue_url="https://github.com/owner/repo/issues/1",
    )
    with pytest.raises(ValueError, match="ticket_not_found"):
        create_link(body, principal())


def test_link_is_unique_per_ticket_and_issue(ticket_db):
    from backend.models import TicketCreate
    from backend.service import create_ticket

    ticket = create_ticket(TicketCreate(title="Link me"), principal())
    connection = create_connection(
        GitHubConnectionCreate(
            project_id="project-1", owner="owner", repository="repo", credential_name="github"
        ),
        principal(),
    )
    body = GitHubLinkCreate(
        ticket_id=ticket["id"], connection_id=connection["id"], owner="owner", repository="repo",
        issue_number=7, issue_url="https://github.com/owner/repo/issues/7",
    )
    link = create_link(body, principal())
    assert get_link(ticket["id"])["id"] == link["id"]

    with pytest.raises(ValueError, match="github_link_exists"):
        create_link(body.model_copy(update={"ticket_id": ticket["id"]}), principal())


def test_link_and_unlink_enforce_ticket_rights_and_audit(ticket_db):
    from backend.audit import list_events
    from backend.models import TicketCreate
    from backend.service import create_ticket

    ticket = create_ticket(TicketCreate(title="Audit me"), principal())
    connection = create_connection(
        GitHubConnectionCreate(
            project_id="project-1", owner="owner", repository="repo", credential_name="github"
        ),
        principal(),
    )
    body = GitHubLinkCreate(
        ticket_id=ticket["id"], connection_id=connection["id"], owner="owner", repository="repo",
        issue_number=8, issue_url="https://github.com/owner/repo/issues/8",
    )
    link_ticket(body, principal())
    assert list_events(ticket["id"])[-1]["event_type"] == "github_linked"
    unlink_ticket(ticket["id"], principal())
    assert list_events(ticket["id"])[-1]["event_type"] == "github_unlinked"


def test_link_rejects_non_owner(ticket_db):
    from backend.models import TicketCreate
    from backend.service import create_ticket

    ticket = create_ticket(TicketCreate(title="Nope"), principal())
    connection = create_connection(
        GitHubConnectionCreate(
            project_id="project-1", owner="owner", repository="repo", credential_name="github"
        ),
        principal(),
    )
    body = GitHubLinkCreate(
        ticket_id=ticket["id"], connection_id=connection["id"], owner="owner", repository="repo",
        issue_number=9, issue_url="https://github.com/owner/repo/issues/9",
    )
    with pytest.raises(ValueError, match="ticket_update_forbidden"):
        link_ticket(body, principal("user-other"))
