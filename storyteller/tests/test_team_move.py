"""T1f: Bestehendes Buch in ein eigenes Buch-Projekt umziehen (Plan schreib-team-t1f-umzug.md)."""
from __future__ import annotations

import pytest
from backend import runs, scenes, storage, team, team_jobs, team_notes
from backend._files import StoryError, story_root
from backend.team import move, setup
from conftest import PROJECT_ID


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from backend.agent_tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def moved():
    from hydrahive.projects import config as pc
    made: list[str] = []
    yield made
    for pid in made:
        pc.delete(pid)


def _book(title="Die Verwandlung", words=300):
    b = storage.create_book(PROJECT_ID, {"title": title, "kind": "novel", "model": "claude-sonnet-4-6"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    sid = st["parts"][0]["chapters"][0]["scenes"][0]
    sc = scenes.get_scene(PROJECT_ID, b["id"], sid)
    scenes.save_scene(PROJECT_ID, b["id"], sid, {"text": "Gregor " * words}, sc["version"])
    storage.add_snapshot(PROJECT_ID, b["id"], sid)
    team_notes.add(PROJECT_ID, b["id"], {"kind": "hint", "title": "H", "text": "t", "scene_id": sid, "author": "X"})
    return b["id"], sid


def _move(moved, bid, **kw):
    out = move.move_book("testuser", PROJECT_ID, bid, **kw)
    moved.append(out["project_id"])
    return out


def test_move_creates_book_project_with_team_and_same_book(moved):
    from hydrahive.projects import config as pc
    bid, sid = _book()
    out = _move(moved, bid)
    p = pc.get(out["project_id"])
    assert out["book_id"] == bid
    assert p["name"] == "Die Verwandlung" and p["created_by"] == "testuser"
    assert p["metadata"]["storyteller"] == {"book_id": bid, "team_version": team.TEAM_VERSION}
    assert len(p["allowed_specialists"]) == len(team.HELPERS)
    book = storage.get_book(out["project_id"], bid)
    assert book["title"] == "Die Verwandlung" and book["model"] == "claude-sonnet-4-6"
    assert book["moved_from"]["project_id"] == PROJECT_ID and book["moved_from"]["at"]
    assert scenes.get_scene(out["project_id"], bid, sid)["text"].startswith("Gregor ")
    assert [n["title"] for n in team_notes.list_notes(out["project_id"], bid)] == ["H"]
    assert len(storage.list_snapshots(out["project_id"], bid, sid)) == 1


def test_source_goes_to_trash_not_deleted(moved):
    bid, _sid = _book()
    out = _move(moved, bid)
    with pytest.raises(StoryError):
        storage.get_book(PROJECT_ID, bid)
    backup = story_root(PROJECT_ID) / "trash" / "moved"
    copies = [d for d in backup.iterdir() if d.name.startswith(bid)]
    assert len(copies) == 1 and (copies[0] / "book.json").is_file()
    assert out["backup"] == str(copies[0].relative_to(story_root(PROJECT_ID)))


def test_scene_trash_of_the_book_moves_along(moved):
    bid, _sid = _book()
    extra = scenes.add_scene(PROJECT_ID, bid, storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"][0]["id"],
                             "Weg")["scene"]["id"]
    storage.remove_scene(PROJECT_ID, bid, extra)
    assert (story_root(PROJECT_ID) / "trash" / bid).is_dir()
    out = _move(moved, bid)
    assert (story_root(out["project_id"]) / "trash" / bid / "scenes").is_dir()
    assert not (story_root(PROJECT_ID) / "trash" / bid).exists()


def test_jobs_folder_is_not_taken_along(moved):
    bid, _sid = _book()
    j = team_jobs.create(PROJECT_ID, bid, {"job": "check_scene", "role": "plausibility", "agent_id": "a", "user": "u"})
    team_jobs.finish(PROJECT_ID, bid, j["id"], status="done")
    out = _move(moved, bid)
    assert team_jobs.list_jobs(out["project_id"], bid) == []


def test_refuses_book_project(moved):
    out = setup.create_book_project("testuser", {"title": "Schon eigen", "kind": "novel", "language": "de"},
                                    model="claude-sonnet-4-6")
    moved.append(out["project_id"])
    with pytest.raises(StoryError) as e:
        move.move_book("testuser", out["project_id"], out["book"]["id"])
    assert e.value.code == "already_book_project"


def test_refuses_while_ghostwriter_runs(moved):
    from hydrahive.projects import config as pc
    bid, _sid = _book()
    before = {p["id"] for p in pc.list_all()}
    runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="book", model="m", options={},
                    scene_ids=[])
    with pytest.raises(StoryError) as e:
        move.move_book("testuser", PROJECT_ID, bid)
    assert e.value.code == "run_active" and e.value.status == 409
    assert {p["id"] for p in pc.list_all()} == before          # nichts angelegt
    assert storage.get_book(PROJECT_ID, bid)                   # Quelle unverändert


def test_refuses_while_team_job_active(moved):
    bid, _sid = _book()
    team_jobs.create(PROJECT_ID, bid, {"job": "check_scene", "role": "plausibility", "agent_id": "a", "user": "u"})
    with pytest.raises(StoryError) as e:
        move.move_book("testuser", PROJECT_ID, bid)
    assert e.value.code == "job_active" and e.value.status == 409


def test_failed_check_removes_new_project_and_keeps_source(moved, monkeypatch):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    bid, sid = _book()
    before_p = {p["id"] for p in pc.list_all()}
    before_a = {a["id"] for a in ac.list_all()}
    monkeypatch.setattr(move, "_fingerprint", lambda d: ("anders", id(d)))   # Ziel ≠ Quelle
    with pytest.raises(StoryError) as e:
        move.move_book("testuser", PROJECT_ID, bid)
    assert e.value.code == "move_check_failed"
    assert {p["id"] for p in pc.list_all()} == before_p
    assert {a["id"] for a in ac.list_all()} == before_a
    assert scenes.get_scene(PROJECT_ID, bid, sid)["text"].startswith("Gregor ")
    assert not (story_root(PROJECT_ID) / "trash" / "moved").exists()


def test_failed_copy_removes_new_project(moved, monkeypatch):
    from hydrahive.projects import config as pc
    bid, _sid = _book()
    before = {p["id"] for p in pc.list_all()}

    def boom(*a, **kw):
        raise OSError("Platte voll")
    monkeypatch.setattr(move, "_copy_book", boom)
    with pytest.raises(OSError):
        move.move_book("testuser", PROJECT_ID, bid)
    assert {p["id"] for p in pc.list_all()} == before
    assert storage.get_book(PROJECT_ID, bid)


def test_fingerprint_sees_text_and_scene_count(tmp_path):
    import shutil
    d = tmp_path / "b"
    (d / "scenes").mkdir(parents=True)
    (d / "book.json").write_text("{}")
    (d / "scenes" / "a.md").write_text("eins zwei")
    one = move._fingerprint(d)
    (d / "scenes" / "a.md").write_text("eins zwei drei")
    assert move._fingerprint(d) != one
    shutil.copy(d / "scenes" / "a.md", d / "scenes" / "b.md")
    assert move._fingerprint(d)[0] != one[0]


def test_title_and_model_come_from_the_book(moved):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    bid, _sid = _book(title="Das Schloss")
    out = _move(moved, bid)
    p = pc.get(out["project_id"])
    assert p["name"] == "Das Schloss"
    author = ac.get(p["agent_id"])
    assert author["name"] == "Das Schloss — Autor" and author["llm_model"] == "claude-sonnet-4-6"




def test_drop_project_removes_helpers_even_on_core_without_527(monkeypatch):
    """Ältere Kerne (vor #527) löschen beim Projekt nur den Projekt-Agenten – drop_project räumt die Helfer selbst weg.

    Nachgestellt: vor dem Kern-Löschen wird die Projekt-Bindung der Helfer entfernt, damit der Kern sie nicht findet."""
    import json

    from hydrahive.agents import config as ac
    from hydrahive.agents._paths import config_path
    from hydrahive.projects import config as pc
    team = setup.new_team_project("testuser", "Alt-Kern", "claude-sonnet-4-6")
    helpers = list(team["helpers"].values())
    real_delete = pc.delete

    def core_without_527(project_id):
        for hid in helpers:
            if ac.get(hid) is not None:
                cfg = json.loads(config_path(hid).read_text())
                cfg.pop("project_id", None)
                config_path(hid).write_text(json.dumps(cfg))
        return real_delete(project_id)
    monkeypatch.setattr(pc, "delete", core_without_527)
    setup.drop_project(team["project_id"])
    assert pc.get(team["project_id"]) is None
    assert all(ac.get(h) is None for h in helpers)


def test_book_with_unavailable_model_is_refused_before_anything_happens(moved, monkeypatch):
    """10.10.: Modell des Buchs nicht mehr in der Live-Liste → vorher HTTP 500 mitten im Anlegen. Jetzt vorab
    model_unavailable; kein neues Projekt, Buch bleibt."""
    from hydrahive.agents import config as ac
    from hydrahive.llm import registry
    from hydrahive.projects import config as pc
    bid, sid = _book()
    monkeypatch.setattr(registry, "known_ids", lambda: {"claude-opus-5"})
    before_p, before_a = {p["id"] for p in pc.list_all()}, {a["id"] for a in ac.list_all()}
    with pytest.raises(StoryError) as e:
        move.move_book("testuser", PROJECT_ID, bid)
    assert e.value.code == "model_unavailable" and e.value.detail == {"model": "claude-sonnet-4-6"}
    assert {p["id"] for p in pc.list_all()} == before_p and {a["id"] for a in ac.list_all()} == before_a
    assert scenes.get_scene(PROJECT_ID, bid, sid)["text"].startswith("Gregor ")
