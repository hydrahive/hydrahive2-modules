"""Import ganzer Bücher (Beispielbuch, Übernahme aus dem Entwurf), Kapitel anlegen, Schnappschüsse mit eigenem Text."""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import importer, snapshots, storage
from backend.storage import StoryError

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _payload(**kw):
    return {
        "title": "Die Verwandlung", "kind": "novel", "language": "de", "audience": "Erwachsene", "idea": "Käfer",
        "notes": "Notiz", "model": "",
        "parts": [{"title": "Teil", "chapters": [
            {"title": "Erstes Kapitel", "scenes": [
                {"title": "Erwachen", "summary": "S1", "pov": "Gregor", "status": "done", "text": "Als Gregor erwachte."},
                {"title": "Prokurist", "summary": "S2", "pov": "", "status": "draft", "text": "Es klopfte."}]},
            {"title": "Zweites Kapitel", "scenes": [{"title": "Äpfel", "summary": "", "pov": "", "status": "idea", "text": ""}]},
        ]}],
        "entities": [{"kind": "character", "name": "Gregor", "aliases": ["Samsa"], "description": "Reisender",
                      "fields": [{"key": "Beruf", "value": "Reisender"}]}],
        **kw,
    }


def test_import_creates_complete_book_in_order():
    b = importer.import_book(PROJECT_ID, _payload())
    st = storage.get_structure(PROJECT_ID, b["id"])
    chapters = st["parts"][0]["chapters"]
    assert [c["title"] for c in chapters] == ["Erstes Kapitel", "Zweites Kapitel"]
    texts = [storage.get_scene(PROJECT_ID, b["id"], s)["text"] for s in chapters[0]["scenes"]]
    assert texts == ["Als Gregor erwachte.", "Es klopfte."]
    first = storage.get_scene(PROJECT_ID, b["id"], chapters[0]["scenes"][0])
    assert (first["title"], first["pov"], first["status"], first["version"]) == ("Erwachen", "Gregor", "done", 1)
    (gregor,) = st["entities"]
    assert gregor["aliases"] == ["Samsa"] and len(gregor["id"]) == 32
    assert storage.get_book(PROJECT_ID, b["id"])["notes"] == "Notiz"


@pytest.mark.parametrize("bad", [
    {"title": ""},
    {"kind": "comic"},
    {"parts": []},
    {"parts": [{"title": "T", "chapters": []}]},
    {"parts": [{"title": "T", "chapters": [{"title": "K", "scenes": []}]}]},
    {"parts": [{"title": "T", "chapters": [{"title": "K", "scenes": [{"title": "S", "text": "x" * (storage.MAX_SCENE_BYTES + 1)}]}]}]},
    {"entities": [{"kind": "alien", "name": "X"}]},
])
def test_import_rejects_bad_data_and_leaves_nothing(bad):
    with pytest.raises(StoryError):
        importer.import_book(PROJECT_ID, _payload(**bad))
    assert storage.list_books(PROJECT_ID) == []
    books = storage.books_dir(PROJECT_ID)
    assert not books.exists() or list(books.iterdir()) == []


def test_import_write_error_midway_leaves_no_half_book(monkeypatch):
    """Scheitert das Schreiben nach einigen Dateien (Platte voll), bleibt kein Rest-Ordner liegen."""
    calls = {"n": 0}
    real = importer.write_json

    def flaky(path, data):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("Platte voll")
        return real(path, data)
    monkeypatch.setattr(importer, "write_json", flaky)
    with pytest.raises(OSError):
        importer.import_book(PROJECT_ID, _payload())
    assert storage.list_books(PROJECT_ID) == []
    assert list(storage.books_dir(PROJECT_ID).iterdir()) == []


def test_import_scene_limit(monkeypatch):
    monkeypatch.setattr(storage, "MAX_SCENES", 2)
    with pytest.raises(StoryError):
        importer.import_book(PROJECT_ID, _payload())


def test_scene_limit_applies_to_add_scene_and_add_chapter(monkeypatch):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    part, ch = st["parts"][0]["id"], st["parts"][0]["chapters"][0]["id"]
    monkeypatch.setattr(storage, "MAX_SCENES", 2)
    import backend.scenes as scenes_mod
    monkeypatch.setattr(scenes_mod, "MAX_SCENES", 2)
    storage.add_scene(PROJECT_ID, b["id"], ch, title="zwei")
    with pytest.raises(StoryError):
        storage.add_scene(PROJECT_ID, b["id"], ch, title="drei")
    with pytest.raises(StoryError):
        storage.add_chapter(PROJECT_ID, b["id"], part, title="K", scene_title="S")
    assert sum(len(c["scenes"]) for c in storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"]) == 2


def test_add_chapter_creates_chapter_with_one_scene():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "nonfiction", "language": "de"})
    part = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["id"]
    r = storage.add_chapter(PROJECT_ID, b["id"], part, title="Kapitel 2", scene_title="Abschnitt 1")
    chapters = r["structure"]["parts"][0]["chapters"]
    assert [c["title"] for c in chapters] == ["Kapitel 1", "Kapitel 2"]
    assert chapters[1]["scenes"] == [r["scene"]["id"]] and r["scene"]["title"] == "Abschnitt 1"
    with pytest.raises(StoryError):
        storage.add_chapter(PROJECT_ID, b["id"], "f" * 32, title="X", scene_title="Y")


def test_snapshot_with_own_text_and_list_without_text():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    snap = snapshots.add_snapshot(PROJECT_ID, b["id"], sid, text="meine Fassung")
    listed = snapshots.list_snapshots(PROJECT_ID, b["id"], sid)
    assert listed[0]["id"] == snap["id"] and "text" not in listed[0] and listed[0]["words"] == 2
    assert snapshots.get_snapshot(PROJECT_ID, b["id"], sid, snap["id"])["text"] == "meine Fassung"
    for bad in ("../x", "2026", "x" * 21, ".hidden", "20261006T120000000000.md"):
        with pytest.raises(StoryError):
            snapshots.get_snapshot(PROJECT_ID, b["id"], sid, bad)
    # Auch eine vorhandene Datei mit falschem Namen wird nicht ausgeliefert (Name wird vor dem Zugriff geprüft).
    stray = storage.book_dir(PROJECT_ID, b["id"]) / "snapshots" / sid / "notiz.md"
    stray.write_text("geheim", encoding="utf-8")
    with pytest.raises(StoryError):
        snapshots.get_snapshot(PROJECT_ID, b["id"], sid, "notiz")
    with pytest.raises(StoryError):
        snapshots.add_snapshot(PROJECT_ID, b["id"], sid, text="x" * (storage.MAX_SCENE_BYTES + 1))


def test_http_import_chapter_and_snapshot(client, auth_headers):
    r = client.post(f"{P}/books/import", json=_payload(), headers=auth_headers)
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    full = client.get(f"{P}/books/{bid}", headers=auth_headers).json()
    part = full["structure"]["parts"][0]["id"]
    r = client.post(f"{P}/books/{bid}/chapters", json={"part_id": part, "title": "Drittes", "scene_title": "Szene 1"}, headers=auth_headers)
    assert r.status_code == 200 and len(r.json()["structure"]["parts"][0]["chapters"]) == 3
    sid = r.json()["scene"]["id"]
    r = client.post(f"{P}/books/{bid}/scenes/{sid}/snapshots", json={"text": "gerettet"}, headers=auth_headers)
    assert r.status_code == 200
    snap = r.json()["id"]
    got = client.get(f"{P}/books/{bid}/scenes/{sid}/snapshots/{snap}", headers=auth_headers)
    assert got.status_code == 200 and got.json()["text"] == "gerettet"
    r = client.delete(f"{P}/books/{bid}/scenes/{sid}", headers=auth_headers)
    assert r.status_code == 400  # letzte Szene des neuen Kapitels bleibt


def test_snapshot_with_same_text_as_newest_is_not_duplicated():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    first = snapshots.add_snapshot(PROJECT_ID, b["id"], sid, text="gleich")
    again = snapshots.add_snapshot(PROJECT_ID, b["id"], sid, text="gleich")
    assert again["id"] == first["id"] and len(snapshots.list_snapshots(PROJECT_ID, b["id"], sid)) == 1
    snapshots.add_snapshot(PROJECT_ID, b["id"], sid, text="anders")
    assert len(snapshots.list_snapshots(PROJECT_ID, b["id"], sid)) == 2


def test_files_and_imported_folders_are_readable_like_the_rest_of_the_workspace():
    """mkstemp/mkdtemp legen 0600/0700 an – Bücher sollen für Projekt-Gruppe/Agenten lesbar sein wie andere Dateien."""
    import stat as st_mod
    b = importer.import_book(PROJECT_ID, _payload())
    d = storage.book_dir(PROJECT_ID, b["id"])
    assert st_mod.S_IMODE(d.stat().st_mode) == st_mod.S_IMODE(storage.books_dir(PROJECT_ID).stat().st_mode)
    for f in [d / "book.json", d / "structure.json", *(d / "scenes").iterdir()]:
        assert st_mod.S_IMODE(f.stat().st_mode) == 0o664, f
