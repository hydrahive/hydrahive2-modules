"""Ablage (Spec §5a): alles wird gespeichert, Fassungen bleiben, Papierkorb statt Löschen, Rechte."""
from __future__ import annotations

import pytest
from backend import store
from conftest import OTHER_PROJECT_ID, PROJECT_ID


def _new(**kw):
    base = {"username": "testuser", "project_id": PROJECT_ID, "session_id": "s1", "agent_id": "a1", "title": "Websuche",
            "kind": "workflow", "html": "<html>1</html>", "source": '{"a": 1}', "source_ext": "json"}
    base.update(kw)
    return store.create(**base)


def test_create_saves_files_and_row(store_dir):
    d = _new()
    assert d["id"].startswith("d_") and len(d["id"]) <= 64
    folder = store_dir / d["id"]
    assert (folder / "diagramm.html").read_text() == "<html>1</html>"
    assert (folder / "eingabe.json").read_text() == '{"a": 1}'
    got = store.get(d["id"])
    assert got["title"] == "Websuche" and got["kind"] == "workflow" and got["project_id"] == PROJECT_ID
    assert got["version_of"] is None and got["deleted_at"] is None
    assert store.html(d["id"]) == "<html>1</html>"


def test_explainer_source_is_markdown(store_dir):
    d = _new(kind="explainer", source="# Antwort", source_ext="md")
    assert (store_dir / d["id"] / "eingabe.md").read_text() == "# Antwort"


def test_new_version_keeps_the_old_one(store_dir):
    a = _new(html="<html>alt</html>")
    b = _new(html="<html>neu</html>", version_of=a["id"])
    assert store.get(b["id"])["version_of"] == a["id"]
    assert store.html(a["id"]) == "<html>alt</html>"
    assert store.html(b["id"]) == "<html>neu</html>"
    assert [v["id"] for v in store.versions(a["id"])] == [a["id"], b["id"]]


def test_version_chain_points_to_the_first(store_dir):
    """Fassung einer Fassung zeigt auf das Ursprungs-Diagramm – eine Kette, kein Baum."""
    a = _new()
    b = _new(version_of=a["id"])
    c = _new(version_of=b["id"])
    assert store.get(c["id"])["version_of"] == a["id"]
    assert [v["id"] for v in store.versions(c["id"])] == [a["id"], b["id"], c["id"]]


def test_trash_and_restore_never_delete_files(store_dir):
    d = _new()
    store.trash(d["id"])
    assert store.get(d["id"])["deleted_at"]
    assert (store_dir / d["id"] / "diagramm.html").exists()
    store.restore(d["id"])
    assert store.get(d["id"])["deleted_at"] is None


def test_unknown_id_and_bad_id(store_dir):
    assert store.get("d_gibtsnicht") is None
    assert store.html("d_gibtsnicht") is None
    for bad in ("../x", "d_a/b", "", "x" * 65):
        assert store.get(bad) is None
        assert store.html(bad) is None


def test_bad_id_never_reaches_the_database(store_dir, monkeypatch):
    """Die ID-Form wird vor jedem Zugriff geprüft – auch wenn es eine Zeile mit so einer ID gäbe."""
    from hydrahive.db.connection import db
    with db() as c:
        c.execute("INSERT INTO module_diagrams (id, username, title, kind, created_at) VALUES (?, ?, ?, ?, ?)",
                  ("../boese", "testuser", "x", "workflow", "2026-10-20T00:00:00Z"))
    try:
        assert store.get("../boese") is None and store.html("../boese") is None
    finally:
        with db() as c:
            c.execute("DELETE FROM module_diagrams WHERE id = ?", ("../boese",))


def test_html_of_trashed_diagram_is_still_readable(store_dir):
    """Nachschlagen im Papierkorb soll gehen."""
    d = _new()
    store.trash(d["id"])
    assert store.html(d["id"]) == "<html>1</html>"


@pytest.mark.parametrize(("user", "role", "ok"), [
    ("testuser", "user", True),     # hat es erstellt
    ("boss", "admin", True),        # Admin
    ("other", "user", False),       # fremd, nicht im Projekt
])
def test_can_view(store_dir, user, role, ok):
    d = _new()
    assert store.can_view(store.get(d["id"]), user, role) is ok


def test_project_member_can_view(store_dir, monkeypatch):
    d = _new(username="jemand", project_id=PROJECT_ID)
    assert store.can_view(store.get(d["id"]), "testuser", "user")       # Mitglied von PROJECT_ID
    e = _new(username="jemand", project_id=OTHER_PROJECT_ID)
    assert not store.can_view(store.get(e["id"]), "testuser", "user")


def test_without_project_only_owner_and_admin(store_dir):
    d = _new(project_id=None)
    row = store.get(d["id"])
    assert store.can_view(row, "testuser", "user")
    assert store.can_view(row, "boss", "admin")
    assert not store.can_view(row, "other", "user")


def test_list_for_user_newest_first_without_trash(store_dir):
    a = _new(title="A")
    b = _new(title="B")
    c = _new(title="C")
    store.trash(c["id"])
    _new(username="other", project_id=OTHER_PROJECT_ID, title="fremd")
    ids = [d["id"] for d in store.list_for("testuser", "user")]
    assert ids[:2] == [b["id"], a["id"]] and c["id"] not in ids
    assert all(d["title"] != "fremd" for d in store.list_for("testuser", "user"))
