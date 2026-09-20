from __future__ import annotations

import json
from pathlib import Path


EXPECTED_TABLES = {
    "module_tickets",
    "module_ticket_comments",
    "module_ticket_teams",
    "module_ticket_team_members",
    "module_ticket_events",
    "module_ticket_notifications",
    "module_ticket_attachments",
    "module_ticket_sla_profiles",
    "module_ticket_saved_views",
    "module_ticket_github_connections",
    "module_ticket_github_links",
}


def test_manifest_declares_internal_tickets_module():
    manifest = json.loads(
        (Path(__file__).parents[1] / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["id"] == "tickets"
    assert manifest["version"] == "0.8.1"
    assert manifest["has_service"] is False
    assert manifest["min_core_version"] == "2.0.0"


def test_register_exposes_router_and_migrations():
    from backend import register

    class Context:
        def __init__(self):
            self.routers = []
            self.tools = []
            self.migrations = []

        def register_router(self, router):
            self.routers.append(router)

        def register_tool(self, tool):
            self.tools.append(tool)

        def register_migrations(self, path):
            self.migrations.append(path)

    context = Context()
    register(context)

    assert len(context.routers) == 1
    assert [tool.name for tool in context.tools] == [
        "ticket_list", "ticket_read", "ticket_create", "ticket_comment",
        "ticket_update", "ticket_create_task", "github_project_list", "github_project_read",
        "ticket_github_read", "ticket_github_link", "ticket_github_unlink",
    ]
    assert context.migrations == ["migrations"]


def test_migration_creates_all_tables(ticket_db):
    from hydrahive.db.connection import db

    with db() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name LIKE 'module_ticket%'"
        ).fetchall()
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(module_ticket_github_links)").fetchall()
        }

    assert {row["name"] for row in rows} == EXPECTED_TABLES
    assert {"remote_title", "remote_body", "remote_state", "remote_labels_json", "remote_assignees_json", "remote_updated_at"} <= columns


def test_migration_is_idempotent(ticket_db):
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("tickets", Path(__file__).parents[1] / "migrations")

    from hydrahive.db.connection import db

    with db() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name LIKE 'module_ticket%'"
        ).fetchall()

    assert {row["name"] for row in rows} == EXPECTED_TABLES
