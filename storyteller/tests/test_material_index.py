"""A4: Material ohne Volltexte – bytegleich zum bisherigen Weg, aber linear statt quadratisch (Spec leistung-a4.md §2)."""
from __future__ import annotations

import builtins
from pathlib import Path

import pytest
from conftest import PROJECT_ID

from backend import ghost, storage
from backend._files import StoryError


def _reference(project_id, book_id, scene_id, memory_chars=ghost._MEMORY, interview=None):
    """Der bisherige Weg (bis 0.16.0) als Referenz: alle früheren Szenen komplett lesen."""
    st = storage.get_structure(project_id, book_id)
    scene = storage.get_scene(project_id, book_id, scene_id)
    order = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
    i = order.index(scene_id)
    earlier = [storage.get_scene(project_id, book_id, s) for s in order[:i]]
    memory = "\n".join(f"- {s['title']}: {s['summary']}" for s in earlier if s["summary"].strip())
    memory = memory[-memory_chars:] if len(memory) > memory_chars else memory
    prev_end = earlier[-1]["text"][-ghost._PREV_END:] if earlier else ""
    return memory, prev_end, scene


def _book(n=12):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de", "idea": "Mia auf Helgoland."})
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": "e" * 32, "kind": "character", "name": "Mia", "aliases": ["Mi"], "description": "Zwölf.",
                       "fields": [{"key": "Augen", "value": "blau"}]}]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    ch = st["parts"][0]["chapters"][0]
    sids = [ch["scenes"][0]]
    for i in range(1, n):
        if i == 6:   # zweites Kapitel
            r = storage.add_chapter(PROJECT_ID, b["id"], st["parts"][0]["id"], "Kapitel 2", "S6")
            sids.append(r["scene"]["id"])
            continue
        chapter = next(c for p in storage.get_structure(PROJECT_ID, b["id"])["parts"] for c in p["chapters"] if sids[-1] in c["scenes"])
        sids.append(storage.add_scene(PROJECT_ID, b["id"], chapter["id"], f"S{i}", after=sids[-1])["scene"]["id"])
    for i, sid in enumerate(sids):
        data = {"text": f"Text von Szene {i}. " * (40 + i) + ("Mia lacht." if i % 3 == 0 else "")}
        if i != 4:                                   # Szene 4 ohne Zusammenfassung (fehlt im Gedächtnis)
            data["summary"] = f"In Szene {i} passiert etwas mit Mia." + (" Lang. " * 200 if i == 2 else "")
        if i == 7:
            data["pov"] = "Mia"
        storage.save_scene(PROJECT_ID, b["id"], sid, data, base_version=storage.get_scene(PROJECT_ID, b["id"], sid)["version"])
    storage.update_book(PROJECT_ID, b["id"], {"ghost": {"length_words": 300}},
                        base_version=storage.get_book(PROJECT_ID, b["id"])["version"])
    return b["id"], sids


@pytest.mark.parametrize("memory_chars", [ghost._MEMORY, 300])
def test_material_is_byte_identical_for_every_scene(memory_chars):
    bid, sids = _book()
    idx = ghost.MemoryIndex.load(PROJECT_ID, bid)
    for sid in sids:
        if sid == sids[4]:
            continue                                 # ohne Zusammenfassung → summary_required (eigener Test)
        memory, prev_end, scene = _reference(PROJECT_ID, bid, sid, memory_chars)
        a = ghost.build_material(PROJECT_ID, bid, sid, memory_chars=memory_chars)
        b = ghost.build_material(PROJECT_ID, bid, sid, memory_chars=memory_chars, index=idx)
        assert a == b
        assert (f"BISHER GESCHAH:\n{memory}" in a.prompt) == bool(memory)
        assert prev_end[-200:] in a.prompt
        assert a.mode == ("proposal" if scene["text"].strip() else "fill")


def test_scene_without_summary_still_needs_it_and_index_does_not_change_that():
    bid, sids = _book()
    for idx in (None, ghost.MemoryIndex.load(PROJECT_ID, bid)):
        with pytest.raises(StoryError) as exc:
            ghost.build_material(PROJECT_ID, bid, sids[4], index=idx)
        assert exc.value.code == "summary_required"


def test_index_follows_new_summaries_after_update():
    """Im Lauf ändert eine geschriebene Szene ihre Zusammenfassung/Text → der Index wird nachgezogen."""
    bid, sids = _book(4)
    idx = ghost.MemoryIndex.load(PROJECT_ID, bid)
    s1 = storage.get_scene(PROJECT_ID, bid, sids[1])
    storage.save_scene(PROJECT_ID, bid, sids[1], {"summary": "NEU: Mia findet den Brief.", "text": "Ganz neuer Schluss."},
                       base_version=s1["version"])
    idx.refresh(sids[1])
    m = ghost.build_material(PROJECT_ID, bid, sids[2], index=idx)
    assert "NEU: Mia findet den Brief." in m.prompt and "Ganz neuer Schluss." in m.prompt
    assert m == ghost.build_material(PROJECT_ID, bid, sids[2])


def _count_text_reads(fn):
    n = {"md": 0}
    orig_rt, orig_open = Path.read_text, builtins.open

    def rt(self, *a, **k):
        if str(self).endswith(".md"):
            n["md"] += 1
        return orig_rt(self, *a, **k)

    def op(f, *a, **k):
        if str(f).endswith(".md"):
            n["md"] += 1
        return orig_open(f, *a, **k)
    Path.read_text, builtins.open = rt, op
    try:
        fn()
    finally:
        Path.read_text, builtins.open = orig_rt, orig_open
    return n["md"]


def test_material_reads_only_this_and_the_previous_scene_text():
    bid, sids = _book(12)
    assert _count_text_reads(lambda: ghost.build_material(PROJECT_ID, bid, sids[-1])) <= 2


def test_plan_for_many_scenes_reads_each_text_at_most_once():
    from backend import run_plan
    bid, sids = _book(12)
    reads = _count_text_reads(lambda: run_plan.plan(PROJECT_ID, bid, scope="book", skip_filled=False))
    assert reads <= 2 * len(sids)        # heute: n² / 2 (≈ 78 bei 12 Szenen)


def test_previous_end_is_the_end_and_first_scene_has_none():
    bid, sids = _book(3)
    s0 = storage.get_scene(PROJECT_ID, bid, sids[0])
    long = "ANFANG " + "mitte " * 600 + "SCHLUSSWORT."
    storage.save_scene(PROJECT_ID, bid, sids[0], {"text": long}, base_version=s0["version"])
    m1 = ghost.build_material(PROJECT_ID, bid, sids[1])
    assert "SCHLUSSWORT." in m1.prompt and "ANFANG" not in m1.prompt
    m0 = ghost.build_material(PROJECT_ID, bid, sids[0])
    assert "ENDE DER VORIGEN SZENE" not in m0.prompt


def test_given_index_is_used_and_not_loaded_again(monkeypatch):
    bid, sids = _book(4)
    idx = ghost.MemoryIndex.load(PROJECT_ID, bid)
    monkeypatch.setattr(ghost.MemoryIndex, "load", classmethod(lambda cls, p, b: (_ for _ in ()).throw(AssertionError("neu geladen"))))
    ghost.build_material(PROJECT_ID, bid, sids[3], index=idx)


def test_plan_counts_an_emptied_scene_as_empty():
    """Text gelöscht → words = 0 → „ohne Text“ (wird geschrieben, nicht übersprungen)."""
    from backend import run_plan
    bid, sids = _book(3)
    s = storage.get_scene(PROJECT_ID, bid, sids[1])
    storage.save_scene(PROJECT_ID, bid, sids[1], {"text": ""}, base_version=s["version"])
    p = run_plan.plan(PROJECT_ID, bid, scope="book", skip_filled=True)
    assert p["scene_ids"] == [sids[1]] and p["skipped_filled"] == 2
