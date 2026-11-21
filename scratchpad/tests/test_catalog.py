"""Ideen als Katalog-Quelle (Föderations-Katalog Etappe 2, Q3).

Anmeldung am neuen Kern, unverändertes Verhalten am alten Kern ohne die
Methoden, catalog_changed an allen Schreibstellen (store, notes, board_link,
task_link), Metadaten nach Spec und Sortierung/after bei gleichen Zeitstempeln.
"""
from __future__ import annotations

import pytest
from helpers import PROJECT_A

from backend import board_link, catalog, notes, store, task_link

STAMP = "2026-11-21T10:00:00.500000Z"


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


def _insert(idea_id: str, username: str = "alice", updated_at: str = STAMP, **extra):
    from hydrahive.db.connection import db
    values = {"id": idea_id, "username": username, "title": f"I {idea_id}", "body": "geheim",
              "created_at": STAMP, "updated_at": updated_at, **extra}
    cols = ", ".join(values)
    with db() as conn:
        conn.execute(f"INSERT INTO module_scratchpad_ideas ({cols}) VALUES ({', '.join('?' for _ in values)})",
                     list(values.values()))


# --- Anmeldung ------------------------------------------------------------

def test_alter_kern_ohne_methoden_modul_laeuft_unveraendert():
    ctx = _register(OldCtx())
    assert sorted(ctx.tools) == ["idea_list", "idea_read", "idea_write", "read_scratchpad"]
    assert ctx.migrations == "migrations" and len(ctx.routers) == 1
    assert catalog._ctx is None
    idea = store.create("alice", title="läuft ohne Katalog")
    assert store.update("alice", idea["id"], status="review")["status"] == "review"
    assert notes.add("alice", idea["id"], author="agent", body="Hinweis") is not None
    assert task_link.create("alice", idea["id"])["task_id"]
    assert store.delete("alice", idea["id"]) is True


def test_neuer_kern_meldet_quelle_idea_an():
    ctx = _register(NewCtx())
    assert len(ctx.sources) == 1
    kind, list_changed, list_versions, get_full, query = ctx.sources[0]
    assert kind == "idea"
    assert (list_changed, list_versions, get_full, query) == (
        catalog.list_changed, catalog.list_versions, catalog.get_full, catalog.query)


def test_echter_modulecontext_des_kerns():
    """Mit dem ModuleContext des Kerns (ab PR #736): Quelle landet in ctx.catalog_sources."""
    context = pytest.importorskip("hydrahive.modules.context")
    ctx = context.ModuleContext("scratchpad")
    if not hasattr(ctx, "register_catalog_source"):
        pytest.skip("Kern ohne Katalog-Quellen")
    _register(ctx)
    assert [s.kind for s in ctx.catalog_sources] == ["idea"]
    store.create("alice", title="echter Kern")  # catalog_changed wirft nie


def test_kaputtes_catalog_changed_bricht_schreiben_nicht():
    class Broken(NewCtx):
        def catalog_changed(self, *a):
            raise RuntimeError("kaputt")
    _register(Broken())
    idea = store.create("alice", title="trotzdem gespeichert")
    assert store.get("alice", idea["id"]) is not None


# --- Schreibstellen ---------------------------------------------------------

def test_store_create_update_delete():
    ctx = _register(NewCtx())
    idea = store.create("alice", title="neu")
    store.update("alice", idea["id"], title="geändert")
    store.update("alice", idea["id"])                  # nichts geändert → keine Meldung
    store.update("bob", idea["id"], title="fremd")     # fremd → keine Meldung
    store.delete("alice", idea["id"])
    store.delete("alice", idea["id"])                  # schon weg → keine Meldung
    assert ctx.changes == [("idea", "alice", idea["id"])] * 3


def test_anmerkung_meldet_idee():
    idea = store.create("alice", title="mit Anmerkung")
    ctx = _register(NewCtx())
    notes.add("alice", idea["id"], author="agent", body="Hinweis")
    notes.add("bob", idea["id"], author="agent", body="fremd")  # fremd → keine Meldung
    assert ctx.changes == [("idea", "alice", idea["id"])]


def test_board_link_meldet_idee_nur_bei_neuem_board():
    idea = store.create("alice", title="mit Board", project_id=PROJECT_A)
    ctx = _register(NewCtx())
    _, created = board_link.create("alice", idea["id"])
    _, again = board_link.create("alice", idea["id"])  # schon verknüpft → nichts geändert
    assert (created, again) == (True, False)
    assert ctx.changes == [("idea", "alice", idea["id"])]


def test_task_link_meldet_neuen_task_und_idee():
    idea = store.create("alice", title="wird Task")
    ctx = _register(NewCtx())
    linked = task_link.create("alice", idea["id"])
    assert ctx.changes == [("task", "alice", linked["task_id"]), ("idea", "alice", idea["id"])]


def test_fehlgeschlagenes_schreiben_meldet_nichts():
    idea = store.create("alice", title="schon verknüpft")
    task_link.create("alice", idea["id"])
    ctx = _register(NewCtx())
    with pytest.raises(store.IdeaError):
        task_link.create("alice", idea["id"])
    with pytest.raises(store.IdeaError):
        store.update("alice", idea["id"], status="gibt-es-nicht")
    assert ctx.changes == []


# --- Metadaten --------------------------------------------------------------

def test_metadaten_genau_nach_spec():
    _insert("i-meta", title="x" * 400, status="planned", task_id="t1", board_id=7)
    [row] = catalog.list_changed("alice", None, 10)
    assert set(row) == {"kind", "item_id", "owner", "title", "status", "priority",
                        "project_id", "project_name", "created_at", "updated_at"}
    assert row["kind"] == "idea" and row["owner"] == "alice" and row["priority"] is None
    assert len(row["title"]) == 300
    assert row["updated_at"] == STAMP  # Wert der Quelle, unverändert


def test_projektname_vom_client_aufgeloest():
    _insert("i-proj", project_id=PROJECT_A)
    [row] = catalog.list_changed("alice", None, 10)
    assert (row["project_id"], row["project_name"]) == (PROJECT_A, "Projekt alice")


def test_get_full_mit_text_und_anmerkungen_nur_eigene():
    idea = store.create("alice", title="voll", body="der Text")
    notes.add("alice", idea["id"], author="agent", body="erste", agent_name="Hydra")
    full = catalog.get_full("alice", idea["id"])
    assert full["body"] == "der Text"
    assert [(n["author"], n["agent_name"], n["body"]) for n in full["notes"]] == [("agent", "Hydra", "erste")]
    assert catalog.get_full("bob", idea["id"]) is None


# --- Sortierung und after ------------------------------------------------

def test_list_changed_gleiche_zeitstempel_sortiert_nach_id_und_after():
    for iid in ("i-c", "i-a", "i-b"):
        _insert(iid, updated_at=STAMP)
    _insert("i-z", updated_at="2026-11-21T10:00:00.499999Z")
    _insert("i-later", updated_at="2026-11-21T10:00:00.500001Z")
    _insert("i-bob", username="bob")
    ids = [r["item_id"] for r in catalog.list_changed("alice", None, 100)]
    assert ids == ["i-z", "i-a", "i-b", "i-c", "i-later"]
    after = [r["item_id"] for r in catalog.list_changed("alice", (STAMP, "i-a"), 100)]
    assert after == ["i-b", "i-c", "i-later"]
    assert [r["item_id"] for r in catalog.list_changed("alice", (STAMP, "i-a"), 1)] == ["i-b"]


def test_list_versions_und_query():
    _insert("i-1", status="new", project_id=PROJECT_A)
    _insert("i-2", status="done", title="Garten planen", updated_at="2026-11-21T11:00:00.000000Z")
    assert catalog.list_versions("alice") == [
        ("i-1", STAMP, PROJECT_A), ("i-2", "2026-11-21T11:00:00.000000Z", None)]
    assert [r["item_id"] for r in catalog.query(["alice"], None, None, None, 10, 0)] == ["i-2", "i-1"]
    assert [r["item_id"] for r in catalog.query(["alice"], PROJECT_A, None, None, 10, 0)] == ["i-1"]
    assert [r["item_id"] for r in catalog.query(["alice"], None, "done", "garten", 10, 0)] == ["i-2"]
    assert catalog.query(["bob"], None, None, None, 10, 0) == []
