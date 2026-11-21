"""Föderations-Katalog Etappe 2 (Q3): Ticket legt Task an → catalog_changed("task", …).

Alter Kern ohne catalog_changed: Modul läuft unverändert. Fehlgeschlagenes
Anlegen meldet nichts, eine kaputte Meldung bricht das Anlegen nicht.
"""
from __future__ import annotations

import pytest

from _hh_isolation import only_own_rows
from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from backend import catalog
from backend.models import TicketCreate
from backend.service import TicketServiceError, create_ticket
from backend.task_link import TaskLinkCreate, create_linked_task


class OldCtx:
    """Kern vor Etappe 2: kennt catalog_changed nicht."""

    def __init__(self):
        self.tools, self.routers, self.migrations = [], [], None

    def register_tool(self, tool):
        self.tools.append(tool.name)

    def register_router(self, router):
        self.routers.append(router)

    def register_migrations(self, rel):
        self.migrations = rel


class NewCtx(OldCtx):
    def __init__(self):
        super().__init__()
        self.changes = []

    def register_catalog_source(self, *a):
        raise AssertionError("tickets ist keine Katalog-Quelle")

    def catalog_changed(self, kind, username, item_id):
        self.changes.append((kind, username, item_id))


@pytest.fixture(autouse=True)
def _unbind():
    catalog._ctx = None
    yield
    catalog._ctx = None


@pytest.fixture
def tasks_table(ticket_db):
    with db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS module_tasks ("
            "id TEXT PRIMARY KEY, username TEXT NOT NULL, project_id TEXT, session_id TEXT, "
            "title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'medium', "
            "status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL DEFAULT 'now', "
            "updated_at TEXT NOT NULL DEFAULT 'now')"
        )
    with only_own_rows("module_tasks"):
        yield


def _principal() -> AuthPrincipal:
    return AuthPrincipal("user-member", "member", "user")


def _register(ctx):
    from backend import register
    register(ctx)
    return ctx


def _link(ticket_id: str) -> dict:
    return create_linked_task(TaskLinkCreate(ticket_id=ticket_id), _principal(),
                              project_id="project-1", session_id=None, actor_id="agent-1")


def test_alter_kern_ohne_methode_modul_laeuft_unveraendert(tasks_table):
    ctx = _register(OldCtx())
    assert ctx.migrations == "migrations" and len(ctx.routers) == 1 and ctx.tools
    assert catalog._ctx is None
    ticket = create_ticket(TicketCreate(title="alter Kern"), _principal())
    assert _link(ticket["id"])["username"] == "member"


def test_ticket_legt_task_an_meldet_task(tasks_table):
    ctx = _register(NewCtx())
    ticket = create_ticket(TicketCreate(title="neuer Kern"), _principal())
    task = _link(ticket["id"])
    assert ctx.changes == [("task", "member", task["id"])]


def test_fehlgeschlagenes_anlegen_meldet_nichts(tasks_table):
    ticket = create_ticket(TicketCreate(title="schon verknüpft"), _principal())
    _link(ticket["id"])
    ctx = _register(NewCtx())
    with pytest.raises(TicketServiceError):
        _link(ticket["id"])
    with pytest.raises(TicketServiceError):
        _link("gibt-es-nicht")
    assert ctx.changes == []


def test_kaputtes_catalog_changed_bricht_anlegen_nicht(tasks_table):
    class Broken(NewCtx):
        def catalog_changed(self, *a):
            raise RuntimeError("kaputt")
    _register(Broken())
    ticket = create_ticket(TicketCreate(title="trotzdem"), _principal())
    assert _link(ticket["id"])["id"]
