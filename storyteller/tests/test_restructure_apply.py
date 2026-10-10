"""C2: Gliederungs-Umbau ausführen (direkt) bzw. als Vorschlag ablegen/übernehmen/verwerfen (Spec autor-gliederung-c2.md)."""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import (
    _replaced,
    chapter_summaries,
    restructure,
    runs,
    storage,
    trash,
    trash_chapters,
)
from backend._files import StoryError

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book(kind="novel"):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": kind, "language": "de"})
    bid = b["id"]
    st = storage.get_structure(PROJECT_ID, bid)
    part = st["parts"][0]["id"]
    a = st["parts"][0]["chapters"][0]["id"]
    s1 = st["parts"][0]["chapters"][0]["scenes"][0]
    s2 = storage.add_scene(PROJECT_ID, bid, a, "Zwei", after=s1)["scene"]["id"]
    r = storage.add_chapter(PROJECT_ID, bid, part, "Leer", "A1")
    b_ = r["structure"]["parts"][0]["chapters"][1]["id"]
    sc = storage.get_scene(PROJECT_ID, bid, s2)
    storage.save_scene(PROJECT_ID, bid, s2, {"text": "Wichtig.", "summary": "Z."}, base_version=sc["version"])
    return bid, a, b_, s1, s2, r["scene"]["id"]


def _titles(bid):
    return [c["title"] for p in storage.get_structure(PROJECT_ID, bid)["parts"] for c in p["chapters"]]


STEPS = lambda a, b, s2: [
    {"op": "delete_chapter", "chapter_id": b},
    {"op": "rename_chapter", "chapter_id": a, "title": "Der Anfang"},
    {"op": "add_chapter", "title": "Neu", "scenes": [{"title": "N1", "summary": "Passiert."}]},
    {"op": "move_scene", "scene_id": s2, "chapter_id": "new:1"},
    {"op": "set_chapter_summary", "chapter_id": "new:1", "summary": "Kapitel neu."},
]


# --- direkt ------------------------------------------------------------------------------------------------------

def test_execute_applies_everything_in_one_structure_change():
    bid, a, b, _s1, s2, _ = _book()
    v = storage.get_structure(PROJECT_ID, bid)["version"]
    out = restructure.execute(PROJECT_ID, bid, STEPS(a, b, s2))
    st = storage.get_structure(PROJECT_ID, bid)
    assert st["version"] == v + 1 and out["structure"] == st
    assert _titles(bid) == ["Der Anfang", "Neu"]
    new_cid = out["ids"]["chapters"]["new:1"]
    n1 = out["ids"]["scenes"]["new:1"]
    assert st["parts"][0]["chapters"][1]["scenes"] == [n1, s2]
    assert storage.get_scene(PROJECT_ID, bid, n1)["summary"] == "Passiert."
    assert storage.get_scene(PROJECT_ID, bid, s2)["text"] == "Wichtig."            # verschoben, nicht kopiert
    assert chapter_summaries.get_all(PROJECT_ID, bid)[new_cid]["summary"] == "Kapitel neu."
    assert [r["chapter_id"] for r in trash_chapters.list_chapters(PROJECT_ID, bid)] == [b]
    assert out["lines"][0].startswith("Kapitel „Leer“ mit 1 Szene(n) löschen")
    assert {s["id"] for s in out["scenes"]} == {n1}


def test_deleted_single_scene_goes_to_scene_trash_and_restores():
    bid, a, _b, s1, s2, _ = _book()
    restructure.execute(PROJECT_ID, bid, [{"op": "delete_scene", "scene_id": s2}])
    rows = trash.list_scenes(PROJECT_ID, bid)
    assert [r["scene_id"] for r in rows] == [s2] and rows[0]["after"] == s1 and rows[0]["chapter_id"] == a
    trash.restore_scene(PROJECT_ID, bid, rows[0]["id"])
    assert storage.get_scene(PROJECT_ID, bid, s2)["text"] == "Wichtig."


def test_invalid_plan_changes_nothing():
    bid, a, _b, _s1, _s2, _ = _book()
    before = storage.get_structure(PROJECT_ID, bid)
    files = sorted(p.name for p in (storage.book_dir(PROJECT_ID, bid) / "scenes").iterdir())
    with pytest.raises(StoryError) as e:
        restructure.execute(PROJECT_ID, bid, [{"op": "add_scene", "chapter_id": a, "title": "x"},
                                             {"op": "delete_scene", "scene_id": "9" * 32}])
    assert e.value.detail["step"] == 2
    assert storage.get_structure(PROJECT_ID, bid) == before
    assert sorted(p.name for p in (storage.book_dir(PROJECT_ID, bid) / "scenes").iterdir()) == files


def test_failure_while_writing_removes_new_scene_files(monkeypatch):
    bid, a, _b, _s1, _s2, _ = _book()
    before = storage.get_structure(PROJECT_ID, bid)
    files = sorted(p.name for p in (storage.book_dir(PROJECT_ID, bid) / "scenes").iterdir())

    def boom(*a, **k):
        raise OSError("Platte voll")
    monkeypatch.setattr(restructure, "_write_structure", boom)
    with pytest.raises(OSError):
        restructure.execute(PROJECT_ID, bid, [{"op": "add_scene", "chapter_id": a, "title": "x"}])
    assert storage.get_structure(PROJECT_ID, bid) == before
    assert sorted(p.name for p in (storage.book_dir(PROJECT_ID, bid) / "scenes").iterdir()) == files


def test_not_while_run_or_job_active(monkeypatch):
    bid, a, *_ = _book()
    monkeypatch.setattr(runs, "active_run", lambda p, b: {"id": "r"})
    with pytest.raises(StoryError) as e:
        restructure.execute(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "x"}])
    assert e.value.code == "run_active"


def test_not_while_team_job_active(monkeypatch):
    from backend import team_jobs
    bid, a, *_ = _book()
    monkeypatch.setattr(team_jobs, "list_jobs", lambda p, b: [{"id": "j", "status": "running"}])
    with pytest.raises(StoryError) as e:
        restructure.execute(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "x"}])
    assert e.value.code == "job_active"
    monkeypatch.setattr(team_jobs, "list_jobs", lambda p, b: [{"id": "j", "status": "done"}])
    restructure.execute(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "x"}])


def test_chapter_summary_version_counts_up():
    """Bestehende Kapitel-Zusammenfassung (Version 1) → nach dem Umbau Version 2 (Konfliktprüfung der Oberfläche)."""
    bid, a, *_ = _book()
    chapter_summaries.save(PROJECT_ID, bid, a, "alt", base_version=0)
    restructure.execute(PROJECT_ID, bid, [{"op": "set_chapter_summary", "chapter_id": a, "summary": "neu"}])
    entry = chapter_summaries.get_all(PROJECT_ID, bid)[a]
    assert entry["summary"] == "neu" and entry["version"] == 2


# --- Vorschlag ---------------------------------------------------------------------------------------------------

def test_propose_stores_and_changes_nothing():
    bid, a, b, _s1, s2, _ = _book()
    before = storage.get_structure(PROJECT_ID, bid)
    p = restructure.propose(PROJECT_ID, bid, STEPS(a, b, s2), author="Buch — Struktur", note="Aufräumen")
    assert storage.get_structure(PROJECT_ID, bid) == before
    got = restructure.get(PROJECT_ID, bid)
    assert got["steps"] == STEPS(a, b, s2) and got["author"] == "Buch — Struktur" and got["note"] == "Aufräumen"
    assert got["lines"][1] == "Kapitel „Kapitel 1“ umbenennen in „Der Anfang“"
    assert got["before"] == ["Kapitel 1", "Leer"] and got["after"] == ["Der Anfang", "Neu"]
    assert got["base_structure_version"] == before["version"] and p["replaced_from"] is None


def test_invalid_proposal_is_not_stored():
    bid, _a, *_ = _book()
    with pytest.raises(StoryError):
        restructure.propose(PROJECT_ID, bid, [{"op": "delete_scene", "scene_id": "9" * 32}], author="X")
    assert restructure.find(PROJECT_ID, bid) is None


def test_second_proposal_replaces_first_into_history():
    bid, a, *_ = _book()
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "Eins"}], author="A")
    p = restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "Zwei"}], author="B")
    assert p["replaced_from"]["author"] == "A"
    assert len(_replaced.history(PROJECT_ID, bid, "restructure", "restructure")) == 1


def test_accept_executes_and_removes_proposal():
    bid, a, b, _s1, s2, _ = _book()
    restructure.propose(PROJECT_ID, bid, STEPS(a, b, s2), author="A")
    out = restructure.accept(PROJECT_ID, bid)
    assert _titles(bid) == ["Der Anfang", "Neu"] and restructure.find(PROJECT_ID, bid) is None
    assert out["structure"] == storage.get_structure(PROJECT_ID, bid)


def test_accept_after_unrelated_change_still_works_but_broken_plan_keeps_proposal():
    bid, a, _b, _s1, s2, _ = _book()
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "Neu"}], author="A")
    storage.add_scene(PROJECT_ID, bid, a, "später dazu")                       # Gliederung geändert, Plan passt noch
    restructure.accept(PROJECT_ID, bid)
    assert _titles(bid)[0] == "Neu"
    restructure.propose(PROJECT_ID, bid, [{"op": "delete_scene", "scene_id": s2}], author="A")
    storage.remove_scene(PROJECT_ID, bid, s2)                                    # Plan passt nicht mehr
    with pytest.raises(StoryError) as e:
        restructure.accept(PROJECT_ID, bid)
    assert e.value.code == "scene_not_found" and restructure.find(PROJECT_ID, bid) is not None


def test_discard_and_restore_from_history():
    bid, a, *_ = _book()
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "X"}], author="A")
    restructure.discard(PROJECT_ID, bid)
    assert restructure.find(PROJECT_ID, bid) is None
    entry = _replaced.history(PROJECT_ID, bid, "restructure", "restructure")[0]
    restructure.restore(PROJECT_ID, bid, entry["id"])
    assert restructure.get(PROJECT_ID, bid)["steps"][0]["title"] == "X"



def test_restore_over_open_proposal_keeps_the_open_one_in_history():
    bid, a, *_ = _book()
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "X"}], author="A")
    restructure.discard(PROJECT_ID, bid)
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "Y"}], author="B")
    old = next(e for e in _replaced.history(PROJECT_ID, bid, "restructure", "restructure") if "„X“" in e["lines"][0])
    restructure.restore(PROJECT_ID, bid, old["id"])
    assert restructure.get(PROJECT_ID, bid)["steps"][0]["title"] == "X"
    kept = [e["lines"][0] for e in _replaced.history(PROJECT_ID, bid, "restructure", "restructure")]
    assert any("„Y“" in line for line in kept)


# --- Routen ------------------------------------------------------------------------------------------------------

def test_routes(client, auth_headers, reader_headers):
    bid, a, _b, _s1, _s2, _ = _book()
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "X"}], author="A")
    url = f"{P}/books/{bid}/proposals/restructure"
    assert client.get(url, headers=reader_headers).json()["steps"][0]["title"] == "X"
    assert client.post(f"{url}/accept", headers=reader_headers).status_code == 403
    r = client.post(f"{url}/accept", headers=auth_headers)
    assert r.status_code == 200 and _titles(bid)[0] == "X"
    assert client.get(url, headers=auth_headers).json() is None
    restructure.propose(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "Y"}], author="A")
    assert client.delete(url, headers=reader_headers).status_code == 403
    assert client.delete(url, headers=auth_headers).status_code == 200 and restructure.find(PROJECT_ID, bid) is None
    full = client.get(f"{P}/books/{bid}", headers=auth_headers).json()
    assert full["restructure_proposal"] is None


def test_structure_route_is_light_and_needs_read(client, auth_headers, reader_headers, other_headers):
    """C2: Die Oberfläche bemerkt direkte Änderungen des Autors über die Version der Gliederung – nur structure.json."""
    bid, a, *_ = _book()
    r = client.get(f"{P}/books/{bid}/structure", headers=reader_headers)
    assert r.status_code == 200 and r.json() == storage.get_structure(PROJECT_ID, bid)
    v = r.json()["version"]
    restructure.execute(PROJECT_ID, bid, [{"op": "rename_chapter", "chapter_id": a, "title": "Neu"}])
    assert client.get(f"{P}/books/{bid}/structure", headers=auth_headers).json()["version"] == v + 1
    assert client.get(f"{P}/books/{bid}/structure", headers=other_headers).status_code == 404
