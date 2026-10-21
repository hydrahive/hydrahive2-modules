"""M1 Schritt 1: Gerüst – Manifest, Kern-Migration, eigener Index mit FTS5 (bzw. Ersatz), register()."""
from __future__ import annotations

import json
import sqlite3

from conftest import MODULE_DIR


def test_manifest():
    m = json.loads((MODULE_DIR / "manifest.json").read_text())
    assert m["id"] == "mailbox" and m["name"] == "Mailbox"
    assert any(c["id"] == "module.mailbox" for c in m["capabilities"])
    assert m["version"].count(".") == 2


def test_kern_migration_nur_kleine_tabellen():
    from hydrahive.db.connection import db
    with db() as c:
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE name LIKE 'module_mailbox_%'")}
    assert {"module_mailbox_accounts", "module_mailbox_sync"} <= names
    assert not any("message" in n or "fts" in n for n in names), "Nachrichten gehören in den eigenen Index"


def test_index_schema_mit_fts(archive):
    from backend import index_db
    with index_db.connect() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
        assert {"folders", "messages", "messages_fts"} <= tables
        assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert (archive / "index.sqlite").exists()
    assert index_db.has_fts() is True


def test_index_ohne_fts5_ersatz(archive, monkeypatch):
    """Mac-brew-Python ohne FTS5: Index entsteht trotzdem, Suche später per LIKE."""
    from backend import index_db
    monkeypatch.setattr(index_db, "_fts5_available", lambda conn: False)
    with index_db.connect() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert "messages" in tables and "messages_fts" not in tables
    assert index_db.has_fts() is False


def test_index_zweimal_oeffnen_ist_harmlos(archive):
    from backend import index_db
    with index_db.connect() as c:
        c.execute("INSERT INTO folders(account_id, name) VALUES ('a1', 'INBOX')")
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM folders").fetchone()[0] == 1


def test_index_fehler_rollt_zurueck(archive):
    from backend import index_db
    try:
        with index_db.connect() as c:
            c.execute("INSERT INTO folders(account_id, name) VALUES ('a1', 'INBOX')")
            raise RuntimeError("abbruch")
    except RuntimeError:
        pass
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM folders").fetchone()[0] == 0


def test_register_meldet_router_job_migrationen():
    import backend
    seen = {"routers": 0, "jobs": [], "migrations": []}

    class Ctx:
        def register_router(self, r): seen["routers"] += 1
        def register_tool(self, t): pass
        def register_job(self, name, fn, **kw): seen["jobs"].append((name, kw))
        def register_migrations(self, d): seen["migrations"].append(d)

    backend.register(Ctx())
    assert seen["routers"] == 1 and seen["migrations"] == ["migrations"]
    assert [n for n, _ in seen["jobs"]] == ["sync"]


def test_index_liegt_unter_data_dir():
    from backend import paths
    from hydrahive.settings import settings
    assert paths.archive_root().is_relative_to(settings.data_dir)
    sqlite3.connect(":memory:").close()


def test_probe_nutzt_genau_die_fts_definition():
    """SQLite < 3.43 kennt fts5 ohne contentless_delete: dann kein FTS statt Absturz beim Anlegen."""
    from backend import index_db

    class Old:
        def __init__(self): self.c = sqlite3.connect(":memory:")
        def execute(self, sql, *a):
            if "contentless_delete" in sql:
                raise sqlite3.OperationalError("unknown option: contentless_delete")
            return self.c.execute(sql, *a)

    assert index_db._fts5_available(Old()) is False
    assert index_db._fts5_available(sqlite3.connect(":memory:")) is True


def test_keine_neuen_status_konstanten():
    """Kern erlaubt fastapi >= 0.111 (Starlette 0.37): dort gibt es HTTP_422_UNPROCESSABLE_CONTENT noch nicht."""
    for f in (MODULE_DIR / "backend").glob("*.py"):
        assert "UNPROCESSABLE_CONTENT" not in f.read_text(), f.name
