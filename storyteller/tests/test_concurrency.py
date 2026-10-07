"""Gleichzeitige Änderungen am selben Buch (Fix 0.6.1, Task 152ab0f0).

Nachbauten aus Tills Prüfliste: zwei gleichzeitige Speichervorgänge auf dieselbe Version waren beide
„erfolgreich“ (einer still überschrieben), 40 gleichzeitige „Szene hinzufügen“ ließen 39 Szenen verwaisen.
"""
from __future__ import annotations

import hashlib
import json
import threading

from conftest import PROJECT_ID

from backend import proposals, storage
from backend.storage import Conflict


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    return b["id"], ch["id"], ch["scenes"][0]


def _parallel(n, fn):
    bar = threading.Barrier(n)
    errors = []

    def run(i):
        bar.wait()
        try:
            fn(i)
        except Exception as exc:  # im Test sammeln, nicht verschlucken
            errors.append(exc)
    ts = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return errors


def _scene_ids(bid):
    st = storage.get_structure(PROJECT_ID, bid)
    return [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]


def _files(bid):
    return {p.stem for p in (storage.book_dir(PROJECT_ID, bid) / "scenes").glob("*.json")}


def test_two_saves_on_same_version_exactly_one_wins():
    for _ in range(60):
        bid, _, sid = _book()
        won = []
        errs = _parallel(2, lambda i: won.append(storage.save_scene(PROJECT_ID, bid, sid, {"text": f"T{i}"}, base_version=1)))
        assert len(won) == 1 and len(errs) == 1 and isinstance(errs[0], Conflict)
        assert storage.get_scene(PROJECT_ID, bid, sid)["text"] == won[0]["text"]


def test_parallel_add_scene_keeps_every_scene_in_the_outline():
    bid, cid, first = _book()
    errs = _parallel(40, lambda i: storage.add_scene(PROJECT_ID, bid, cid, f"S{i}", after=first))
    assert errs == []
    ids = _scene_ids(bid)
    assert len(ids) == 41 and len(set(ids)) == 41 and _files(bid) == set(ids)
    assert storage.get_structure(PROJECT_ID, bid)["version"] == 1 + 40


def test_parallel_add_chapter_and_remove_scene_stay_consistent():
    bid, cid, first = _book()
    extra = [storage.add_scene(PROJECT_ID, bid, cid, f"X{i}")["scene"]["id"] for i in range(10)]
    part = storage.get_structure(PROJECT_ID, bid)["parts"][0]["id"]

    def work(i):
        if i < 10:
            storage.remove_scene(PROJECT_ID, bid, extra[i])
        else:
            storage.add_chapter(PROJECT_ID, bid, part, f"K{i}", f"Szene{i}")
    assert _parallel(20, work) == []
    ids = _scene_ids(bid)
    assert len(ids) == 1 + 10 and set(extra).isdisjoint(ids) and _files(bid) == set(ids)


def test_parallel_save_structure_and_add_scene_never_lose_a_scene():
    bid, cid, first = _book()
    base = storage.get_structure(PROJECT_ID, bid)

    def work(i):
        if i % 2:
            storage.add_scene(PROJECT_ID, bid, cid, f"S{i}")
        else:
            try:
                st = json.loads(json.dumps(base))
                st["parts"][0]["chapters"][0]["title"] = f"Titel {i}"
                storage.save_structure(PROJECT_ID, bid, st, base_version=base["version"])
            except Conflict:
                pass
    assert _parallel(20, work) == []
    assert _files(bid) <= set(_scene_ids(bid)) | set()   # keine Datei ohne Platz in der Gliederung
    assert set(_scene_ids(bid)) <= _files(bid)


def test_proposal_accept_races_with_save_one_conflicts():
    for _ in range(30):
        bid, _, sid = _book()
        proposals.store(PROJECT_ID, bid, sid, "Vorschlag", run_id="r", model="m", base_version=1)
        results = []

        def work(i):
            if i == 0:
                results.append(("accept", proposals.accept(PROJECT_ID, bid, sid, base_version=1)))
            else:
                results.append(("save", storage.save_scene(PROJECT_ID, bid, sid, {"text": "Autor"}, base_version=1)))
        errs = _parallel(2, work)
        assert len(results) == 1 and len(errs) == 1 and isinstance(errs[0], Conflict)


def test_scene_meta_carries_text_hash_and_mismatch_is_detected(caplog):
    bid, _, sid = _book()
    s = storage.save_scene(PROJECT_ID, bid, sid, {"text": "Hallo"}, base_version=1)
    meta = json.loads((storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.json").read_text())
    assert meta["text_sha"] == hashlib.sha256(b"Hallo").hexdigest() and "text_sha" not in s
    # Absturz zwischen .md und .json: neuer Text, alte Meta
    (storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.md").write_text("Neuer Text", encoding="utf-8")
    with caplog.at_level("WARNING"):
        got = storage.get_scene(PROJECT_ID, bid, sid)
    assert got["text"] == "Neuer Text" and got["version"] == s["version"] and "text_sha" not in got
    assert any("passt nicht" in r.getMessage() for r in caplog.records)
    # Nächstes Speichern heilt: Version + 1, Hash stimmt wieder
    healed = storage.save_scene(PROJECT_ID, bid, sid, {"summary": "x"}, base_version=s["version"])
    meta = json.loads((storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.json").read_text())
    assert healed["version"] == s["version"] + 1 and meta["text_sha"] == hashlib.sha256(b"Neuer Text").hexdigest()


def test_old_scene_without_hash_is_fine(caplog):
    bid, _, sid = _book()
    p = storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.json"
    meta = json.loads(p.read_text())
    meta.pop("text_sha", None)
    p.write_text(json.dumps(meta))
    with caplog.at_level("WARNING"):
        assert storage.get_scene(PROJECT_ID, bid, sid)["version"] == 1
    assert not caplog.records


def test_new_books_and_imports_have_text_hash():
    from backend import importer
    bid, _, sid = _book()
    assert "text_sha" in json.loads((storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.json").read_text())
    b = importer.import_book(PROJECT_ID, {"title": "I", "kind": "novel", "language": "de", "parts": [
        {"title": "T", "chapters": [{"title": "K", "scenes": [{"title": "S", "text": "Importiert."}]}]}]})
    isid = _scene_ids(b["id"])[0]
    meta = json.loads((storage.book_dir(PROJECT_ID, b["id"]) / "scenes" / f"{isid}.json").read_text())
    assert meta["text_sha"] == hashlib.sha256("Importiert.".encode()).hexdigest()
