"""C1: Kapitel löschen (mit allen Szenen, in den Papierkorb) und wiederherstellen (Spec loeschen-c1.md)."""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import (
    chapter_summaries,
    interviews,
    runs,
    snapshots,
    storage,
    team_jobs,
    trash,
    trash_chapters,
)
from backend._files import StoryError

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book(chapters=3, per=2):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "nonfiction", "language": "de"})
    bid = b["id"]
    st = storage.get_structure(PROJECT_ID, bid)
    part = st["parts"][0]["id"]
    cids, sids = [st["parts"][0]["chapters"][0]["id"]], [[st["parts"][0]["chapters"][0]["scenes"][0]]]
    for c in range(1, chapters):
        r = storage.add_chapter(PROJECT_ID, bid, part, f"K{c + 1}", "A1")
        cids.append(r["structure"]["parts"][0]["chapters"][c]["id"])
        sids.append([r["scene"]["id"]])
    for c in range(chapters):
        for _ in range(1, per):
            sids[c].append(storage.add_scene(PROJECT_ID, bid, cids[c], "A", after=sids[c][-1])["scene"]["id"])
    return bid, cids, sids


def _chapters(bid):
    return [(c["id"], c["scenes"]) for p in storage.get_structure(PROJECT_ID, bid)["parts"] for c in p["chapters"]]


def _fill(bid, cid, sid):
    s = storage.get_scene(PROJECT_ID, bid, sid)
    storage.save_scene(PROJECT_ID, bid, sid, {"text": "Wichtiger Text hier.", "summary": "Z."}, base_version=s["version"])
    snapshots.add_snapshot(PROJECT_ID, bid, sid, "Alt")
    interviews.save(PROJECT_ID, bid, cid, [{"id": "a" * 32, "question": "Wie?", "answer": "So."}], base_version=0)
    chapter_summaries.save(PROJECT_ID, bid, cid, "Kapitel kurz.", base_version=0)


def test_delete_chapter_removes_it_with_all_scenes_and_keeps_everything_in_trash():
    bid, cids, sids = _book()
    _fill(bid, cids[1], sids[1][0])
    v = storage.get_structure(PROJECT_ID, bid)["version"]
    st = storage.remove_chapter(PROJECT_ID, bid, cids[1])
    assert st["version"] == v + 1 and [c for c, _ in _chapters(bid)] == [cids[0], cids[2]]
    d = storage.book_dir(PROJECT_ID, bid)
    assert not any(s in str(p) for s in sids[1] for p in d.rglob("*"))           # Szenen ganz raus aus dem Buch
    assert not any(cids[1] in str(p) for p in d.rglob("*"))                      # Interview auch
    assert cids[1] not in chapter_summaries._read(PROJECT_ID, bid)              # Kapitel-Zusammenfassung auch
    rows = trash_chapters.list_chapters(PROJECT_ID, bid)
    assert len(rows) == 1
    r = rows[0]
    assert r["chapter_id"] == cids[1] and r["title"] == "K2" and r["scenes"] == 2 and r["words"] == 3 and r["deleted_at"]
    assert trash.list_scenes(PROJECT_ID, bid) == []                              # nicht doppelt als Einzelszenen


def test_restore_chapter_puts_everything_back_at_its_place():
    bid, cids, sids = _book()
    _fill(bid, cids[1], sids[1][0])
    storage.remove_chapter(PROJECT_ID, bid, cids[1])
    out = trash_chapters.restore_chapter(PROJECT_ID, bid, trash_chapters.list_chapters(PROJECT_ID, bid)[0]["id"])
    assert _chapters(bid) == [(cids[0], sids[0]), (cids[1], sids[1]), (cids[2], sids[2])]
    assert out["placed"] == "original" and out["structure"]["version"] == storage.get_structure(PROJECT_ID, bid)["version"]
    assert {s["id"] for s in out["scenes"]} == set(sids[1])
    s = storage.get_scene(PROJECT_ID, bid, sids[1][0])
    assert s["text"] == "Wichtiger Text hier." and s["summary"] == "Z."
    assert [x["words"] for x in snapshots.list_snapshots(PROJECT_ID, bid, sids[1][0])] == [1]
    assert interviews.get(PROJECT_ID, bid, cids[1])["questions"][0]["answer"] == "So."
    assert chapter_summaries.get_all(PROJECT_ID, bid)[cids[1]]["summary"] == "Kapitel kurz."
    assert storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"][1]["title"] == "K2"
    assert trash_chapters.list_chapters(PROJECT_ID, bid) == []


def test_restore_first_chapter_goes_to_the_start():
    bid, cids, _sids = _book()
    storage.remove_chapter(PROJECT_ID, bid, cids[0])
    trash_chapters.restore_chapter(PROJECT_ID, bid, trash_chapters.list_chapters(PROJECT_ID, bid)[0]["id"])
    assert [c for c, _ in _chapters(bid)] == cids


def test_restore_when_previous_chapter_is_gone_goes_to_end_of_part():
    bid, cids, _sids = _book()
    storage.remove_chapter(PROJECT_ID, bid, cids[1])
    storage.remove_chapter(PROJECT_ID, bid, cids[0])
    entry = next(r for r in trash_chapters.list_chapters(PROJECT_ID, bid) if r["chapter_id"] == cids[1])
    out = trash_chapters.restore_chapter(PROJECT_ID, bid, entry["id"])
    assert out["placed"] == "end" and [c for c, _ in _chapters(bid)] == [cids[2], cids[1]]


def test_cannot_delete_the_last_chapter_of_the_book():
    bid, cids, _ = _book(chapters=1)
    with pytest.raises(StoryError) as e:
        storage.remove_chapter(PROJECT_ID, bid, cids[0])
    assert e.value.code == "last_chapter" and e.value.status == 409
    assert [c for c, _ in _chapters(bid)] == cids


def test_unknown_chapter_is_404():
    bid, _, _ = _book(chapters=2)
    with pytest.raises(StoryError) as e:
        storage.remove_chapter(PROJECT_ID, bid, "f" * 32)
    assert e.value.status == 404
    with pytest.raises(StoryError):
        storage.remove_chapter(PROJECT_ID, bid, "../x")


def test_not_while_a_ghostwriter_run_or_team_job_is_active(monkeypatch):
    bid, cids, _ = _book(chapters=2)
    monkeypatch.setattr(runs, "active_run", lambda p, b: {"id": "r"})
    with pytest.raises(StoryError) as e:
        storage.remove_chapter(PROJECT_ID, bid, cids[1])
    assert e.value.code == "run_active" and e.value.status == 409
    monkeypatch.setattr(runs, "active_run", lambda p, b: None)
    monkeypatch.setattr(team_jobs, "list_jobs", lambda p, b: [{"status": "running"}])
    with pytest.raises(StoryError) as e:
        storage.remove_chapter(PROJECT_ID, bid, cids[1])
    assert e.value.code == "job_active"
    assert len(_chapters(bid)) == 2


def test_deleting_the_last_scene_of_a_chapter_takes_the_chapter_along():
    bid, cids, sids = _book(chapters=2, per=1)
    st = storage.remove_scene(PROJECT_ID, bid, sids[1][0])
    assert [c for c, _ in _chapters(bid)] == [cids[0]] and st["version"] == storage.get_structure(PROJECT_ID, bid)["version"]
    assert [r["chapter_id"] for r in trash_chapters.list_chapters(PROJECT_ID, bid)] == [cids[1]]


def test_last_scene_of_the_book_stays():
    bid, _cids, sids = _book(chapters=1, per=1)
    with pytest.raises(StoryError) as e:
        storage.remove_scene(PROJECT_ID, bid, sids[0][0])
    assert e.value.code == "last_chapter"


def test_restore_refuses_when_ids_are_back_and_changes_nothing():
    bid, cids, _sids = _book()
    storage.remove_chapter(PROJECT_ID, bid, cids[1])
    entry = trash_chapters.list_chapters(PROJECT_ID, bid)[0]["id"]
    st = storage.get_structure(PROJECT_ID, bid)
    st["parts"][0]["chapters"].append({"id": cids[1], "title": "Neu", "scenes": st["parts"][0]["chapters"][0]["scenes"][:1]})
    st["parts"][0]["chapters"][0]["scenes"] = st["parts"][0]["chapters"][0]["scenes"][1:]
    storage.save_structure(PROJECT_ID, bid, st, base_version=st["version"])
    before = storage.get_structure(PROJECT_ID, bid)
    with pytest.raises(StoryError) as e:
        trash_chapters.restore_chapter(PROJECT_ID, bid, entry)
    assert e.value.code == "chapter_exists" and e.value.status == 409
    assert storage.get_structure(PROJECT_ID, bid) == before and trash_chapters.list_chapters(PROJECT_ID, bid)


def test_restore_respects_scene_limit(monkeypatch):
    from backend import _book as book_mod
    bid, cids, _ = _book(chapters=2, per=2)
    storage.remove_chapter(PROJECT_ID, bid, cids[1])
    monkeypatch.setattr(trash_chapters, "MAX_SCENES", 3)
    monkeypatch.setattr(book_mod, "MAX_SCENES", 3)
    with pytest.raises(StoryError) as e:
        trash_chapters.restore_chapter(PROJECT_ID, bid, trash_chapters.list_chapters(PROJECT_ID, bid)[0]["id"])
    assert e.value.code == "too_many_scenes"


@pytest.mark.parametrize("bad", ["x", "../../etc", "a" * 32 + "-2026", "a" * 32 + "-20261010T000000000000/.."])
def test_bad_entry_ids_are_404(bad):
    bid, _, _ = _book(chapters=1)
    with pytest.raises(StoryError) as e:
        trash_chapters.restore_chapter(PROJECT_ID, bid, bad)
    assert e.value.status == 404


def test_routes_and_rights(client, auth_headers, reader_headers):
    bid, cids, _sids = _book()
    url = f"{P}/books/{bid}/chapters/{cids[1]}"
    assert client.delete(url, headers=reader_headers).status_code == 403
    r = client.delete(url, headers=auth_headers)
    assert r.status_code == 200 and [c["id"] for c in r.json()["parts"][0]["chapters"]] == [cids[0], cids[2]]
    rows = client.get(f"{P}/books/{bid}/trash/chapters", headers=reader_headers)
    assert rows.status_code == 200 and rows.json()[0]["chapter_id"] == cids[1]
    entry = rows.json()[0]["id"]
    assert client.post(f"{P}/books/{bid}/trash/chapters/{entry}/restore", headers=reader_headers).status_code == 403
    r = client.post(f"{P}/books/{bid}/trash/chapters/{entry}/restore", headers=auth_headers)
    assert r.status_code == 200 and r.json()["placed"] == "original"
    assert client.delete(f"{P}/books/{bid}/chapters/{'f' * 32}", headers=auth_headers).status_code == 404


def test_part_without_chapters_disappears_and_restore_goes_to_last_part():
    """Teil 2 hat nur ein Kapitel: löschen → Teil weg (ein leerer Teil ist ungültig); Wiederherstellen → ans Ende."""
    bid, cids, _sids = _book(chapters=2)
    st = storage.get_structure(PROJECT_ID, bid)
    st["parts"].append({"id": "b" * 32, "title": "Teil 2", "chapters": [st["parts"][0]["chapters"].pop()]})
    storage.save_structure(PROJECT_ID, bid, st, base_version=st["version"])
    st = storage.remove_chapter(PROJECT_ID, bid, cids[1])
    assert [p["id"] for p in st["parts"]] == [storage.get_structure(PROJECT_ID, bid)["parts"][0]["id"]]
    storage.save_structure(PROJECT_ID, bid, st, base_version=st["version"])                # gültig speicherbar
    out = trash_chapters.restore_chapter(PROJECT_ID, bid, trash_chapters.list_chapters(PROJECT_ID, bid)[0]["id"])
    assert out["placed"] == "end" and [c for c, _ in _chapters(bid)] == [cids[0], cids[1]]


def test_entry_name_must_match_exactly_even_if_folder_exists():
    bid, cids, _ = _book(chapters=2)
    storage.remove_chapter(PROJECT_ID, bid, cids[1])
    real = trash_chapters.list_chapters(PROJECT_ID, bid)[0]["id"]
    root = storage.story_root(PROJECT_ID) / "trash" / bid / "chapters"
    (root / "spiel").mkdir()
    (root / real).rename(root / "spiel" / real)
    import shutil
    shutil.copytree(root / "spiel" / real, root / "kopie")
    with pytest.raises(StoryError) as e:
        trash_chapters.restore_chapter(PROJECT_ID, bid, "kopie")
    assert e.value.status == 404
    assert [r["id"] for r in trash_chapters.list_chapters(PROJECT_ID, bid)] == []        # falsch benannt = nicht gelistet


def test_list_is_newest_deletion_first():
    bid, cids, _ = _book(chapters=4)
    for cid in (cids[3], cids[1], cids[2]):
        storage.remove_chapter(PROJECT_ID, bid, cid)
    assert [r["chapter_id"] for r in trash_chapters.list_chapters(PROJECT_ID, bid)] == [cids[2], cids[1], cids[3]]
