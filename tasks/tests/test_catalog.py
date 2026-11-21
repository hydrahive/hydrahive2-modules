"""Tasks als Katalog-Quelle (Föderations-Katalog Etappe 2, Q3).

Anmeldung am neuen Kern, unverändertes Verhalten am alten Kern ohne die
Methoden, catalog_changed an allen Schreibstellen, Metadaten nach Spec und
Sortierung/after bei gleichen Zeitstempeln.
"""
from __future__ import annotations

import pytest

from backend import catalog, service

STAMP = "2026-11-21T10:00:00Z"


class OldCtx:
    """Kern vor Etappe 2: kennt weder register_catalog_source noch catalog_changed."""

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
        self.sources, self.changes = [], []

    def register_catalog_source(self, kind, list_changed, list_versions, get_full, query):
        self.sources.append((kind, list_changed, list_versions, get_full, query))
        return True

    def catalog_changed(self, kind, username, item_id):
        self.changes.append((kind, username, item_id))


@pytest.fixture(autouse=True)
def _unbind():
    catalog._ctx = None
    yield
    catalog._ctx = None


def _register(ctx):
    from backend import register
    register(ctx)
    return ctx


def _insert(task_id: str, username: str = "alice", updated_at: str = STAMP, **extra):
    from hydrahive.db.connection import db
    values = {"id": task_id, "username": username, "title": f"T {task_id}", "description": "geheim",
              "created_at": STAMP, "updated_at": updated_at, **extra}
    cols = ", ".join(values)
    with db() as conn:
        conn.execute(f"INSERT INTO module_tasks ({cols}) VALUES ({', '.join('?' for _ in values)})",
                     list(values.values()))


# --- Anmeldung ------------------------------------------------------------

def test_alter_kern_ohne_methoden_modul_laeuft_unveraendert():
    ctx = _register(OldCtx())
    assert sorted(ctx.tools) == ["task_delete", "task_list", "task_read", "task_write"]
    assert ctx.migrations == "migrations" and len(ctx.routers) == 1
    assert catalog._ctx is None
    task = service.create_task("alice", "läuft ohne Katalog")
    assert service.update_task("alice", task["id"], status="done")["status"] == "done"
    assert service.delete_task("alice", task["id"]) is True


def test_neuer_kern_meldet_quelle_task_an():
    ctx = _register(NewCtx())
    assert len(ctx.sources) == 1
    kind, list_changed, list_versions, get_full, query = ctx.sources[0]
    assert kind == "task"
    assert (list_changed, list_versions, get_full, query) == (
        catalog.list_changed, catalog.list_versions, catalog.get_full, catalog.query)


def test_echter_modulecontext_des_kerns():
    """Mit dem ModuleContext des Kerns (ab PR #736): Quelle landet in ctx.catalog_sources."""
    context = pytest.importorskip("hydrahive.modules.context")
    ctx = context.ModuleContext("tasks")
    if not hasattr(ctx, "register_catalog_source"):
        pytest.skip("Kern ohne Katalog-Quellen")
    _register(ctx)
    assert [s.kind for s in ctx.catalog_sources] == ["task"]
    service.create_task("alice", "echter Kern")  # catalog_changed wirft nie


def test_kaputtes_catalog_changed_bricht_schreiben_nicht():
    class Broken(NewCtx):
        def catalog_changed(self, *a):
            raise RuntimeError("kaputt")
    _register(Broken())
    task = service.create_task("alice", "trotzdem gespeichert")
    assert service.get_task("alice", task["id"]) is not None


# --- Schreibstellen ---------------------------------------------------------

def test_catalog_changed_bei_create_update_delete():
    ctx = _register(NewCtx())
    task = service.create_task("alice", "neu")
    service.update_task("alice", task["id"], title="geändert")
    service.update_task("alice", task["id"])                 # nichts geändert → keine Meldung
    service.update_task("alice", "gibt-es-nicht", title="x")  # unbekannt → keine Meldung
    service.delete_task("alice", task["id"])
    service.delete_task("alice", task["id"])                 # schon weg → keine Meldung
    assert ctx.changes == [("task", "alice", task["id"])] * 3


# --- Metadaten --------------------------------------------------------------

def test_metadaten_genau_nach_spec():
    _insert("t-meta", title="x" * 400, priority="high", session_id="s1", source_kind="idea", source_id="i1")
    [row] = catalog.list_changed("alice", None, 10)
    assert set(row) == {"kind", "item_id", "owner", "title", "status", "priority",
                        "project_id", "project_name", "created_at", "updated_at"}
    assert row["kind"] == "task" and row["owner"] == "alice" and row["priority"] == "high"
    assert len(row["title"]) == 300
    assert row["updated_at"] == STAMP  # Wert der Quelle, unverändert


def test_get_full_mit_beschreibung_nur_eigene():
    _insert("t-full")
    full = catalog.get_full("alice", "t-full")
    assert full["description"] == "geheim" and full["item_id"] == "t-full"
    assert catalog.get_full("bob", "t-full") is None
    assert catalog.get_full("alice", "unbekannt") is None


# --- Sortierung und after ------------------------------------------------

def test_list_changed_gleiche_zeitstempel_sortiert_nach_id_und_after():
    for tid in ("t-c", "t-a", "t-b"):
        _insert(tid, updated_at=STAMP)
    _insert("t-z", updated_at="2026-11-21T09:59:59Z")
    _insert("t-later", updated_at="2026-11-21T10:00:01Z")
    _insert("t-bob", username="bob")
    ids = [r["item_id"] for r in catalog.list_changed("alice", None, 100)]
    assert ids == ["t-z", "t-a", "t-b", "t-c", "t-later"]
    after = [r["item_id"] for r in catalog.list_changed("alice", (STAMP, "t-a"), 100)]
    assert after == ["t-b", "t-c", "t-later"]
    assert [r["item_id"] for r in catalog.list_changed("alice", (STAMP, "t-a"), 1)] == ["t-b"]
    assert catalog.list_changed("alice", ("2026-11-21T10:00:01Z", "t-later"), 100) == []


def test_list_versions_und_query():
    _insert("t-1", status="open", project_id="proj-a")
    _insert("t-2", status="done", title="Rechnung bezahlen", updated_at="2026-11-21T11:00:00Z")
    _insert("t-3", username="bob")
    assert catalog.list_versions("alice") == [("t-1", STAMP, "proj-a"), ("t-2", "2026-11-21T11:00:00Z", None)]
    assert [r["item_id"] for r in catalog.query(["alice", "bob"], None, None, None, 10, 0)][:2] == ["t-2", "t-3"]
    assert [r["item_id"] for r in catalog.query(["alice"], "proj-a", None, None, 10, 0)] == ["t-1"]
    assert [r["item_id"] for r in catalog.query(["alice"], None, "done", None, 10, 0)] == ["t-2"]
    assert [r["item_id"] for r in catalog.query(["alice"], None, None, "rechnung", 10, 0)] == ["t-2"]
    assert [r["item_id"] for r in catalog.query(["alice"], None, None, None, 1, 1)] == ["t-1"]
    assert catalog.query([], None, None, None, 10, 0) == []
    assert catalog.query(["alice"], None, None, "%", 10, 0) == []
