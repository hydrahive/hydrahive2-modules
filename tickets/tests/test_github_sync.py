from __future__ import annotations

from hydrahive.api.middleware.auth import AuthPrincipal
from backend import github


def test_sync_issue_snapshot_is_idempotent(ticket_db):
    principal = AuthPrincipal("user-member", "member", "user")
    connection = {
        "id": "connection-1", "project_id": "project-1", "owner": "gh0stOo",
        "repository": "flowki-studio",
    }
    issue = {
        "id": "I_145", "number": 145, "title": "Remote title", "body": "Remote body",
        "url": "https://github.com/gh0stOo/flowki-studio/issues/145", "state": "OPEN",
        "updatedAt": "2026-09-20T00:00:00Z", "labels": {"nodes": [{"name": "bug"}]},
        "assignees": {"nodes": [{"login": "gh0stOo"}]},
    }
    with __import__("hydrahive.db.connection", fromlist=["db"]).db(immediate=True) as conn:
        conn.execute(
            "INSERT INTO module_ticket_github_connections "
            "(id,project_id,owner,repository,credential_name,created_by) VALUES(?,?,?,?,?,?)",
            (connection["id"], connection["project_id"], connection["owner"], connection["repository"], "project_git_token", principal.user_id),
        )

    first = github.sync_issue_snapshot(connection, issue, principal)
    second = github.sync_issue_snapshot(connection, issue, principal)

    assert first["created"] is True
    assert second["created"] is False
    assert first["ticket"]["id"] == second["ticket"]["id"]
    assert second["link"]["remote_title"] == "Remote title"

    from hydrahive.db.connection import db
    with db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM module_tickets").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM module_ticket_github_links").fetchone()[0] == 1
