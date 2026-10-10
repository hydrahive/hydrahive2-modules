"""C2: Gliederungs-Umbau – Schritte prüfen und auf einer Kopie anwenden (reine Logik, Spec autor-gliederung-c2.md §2)."""
from __future__ import annotations

import copy

import pytest

from backend._files import StoryError
from backend._restructure_plan import MAX_STEPS, describe, plan

A, B, C = "a" * 32, "b" * 32, "c" * 32          # Kapitel
S1, S2, S3, S4 = "1" * 32, "2" * 32, "3" * 32, "4" * 32   # Szenen
P1, P2 = "e" * 32, "f" * 32                     # Teile


def _st():
    return {"version": 7, "entities": [], "parts": [
        {"id": P1, "title": "Teil 1", "chapters": [{"id": A, "title": "Eins", "scenes": [S1, S2]},
                                                  {"id": B, "title": "Zwei", "scenes": [S3]}]},
        {"id": P2, "title": "Teil 2", "chapters": [{"id": C, "title": "Drei", "scenes": [S4]}]}]}


def _ids():
    counter = iter(f"{n:032x}" for n in range(100, 200))
    return lambda: next(counter)


def _order(st):
    return [(c["title"], c["scenes"]) for p in st["parts"] for c in p["chapters"]]


def run(steps, st=None, **kw):
    st = st or _st()
    before = copy.deepcopy(st)
    out = plan(st, steps, new_id=_ids(), **kw)
    assert st == before                                                   # Eingabe bleibt unberührt
    return out


def fails(steps, code, step=None, st=None):
    with pytest.raises(StoryError) as e:
        run(steps, st)
    assert e.value.code == code
    if step is not None:
        assert e.value.detail.get("step") == step
    return e.value


def test_rename_chapter():
    p = run([{"op": "rename_chapter", "chapter_id": B, "title": "  Neu  "}])
    assert _order(p.structure)[1] == ("Neu", [S3]) and p.structure["version"] == 7


def test_add_chapter_at_end_start_and_after_with_scenes():
    p = run([{"op": "add_chapter", "title": "Ende", "scenes": [{"title": "x", "summary": "X."}]},
             {"op": "add_chapter", "title": "Anfang", "after_chapter_id": "", "scenes": [{"title": "y"}]},
             {"op": "add_chapter", "title": "Mitte", "after_chapter_id": A, "scenes": [{"title": "z"}, {"title": "w"}]}])
    titles = [t for t, _ in _order(p.structure)]
    assert titles == ["Anfang", "Eins", "Mitte", "Zwei", "Drei", "Ende"]
    assert [s["title"] for s in p.new_scenes] == ["x", "y", "z", "w"] and p.new_scenes[0]["summary"] == "X."
    assert p.structure["parts"][1]["chapters"][-1]["title"] == "Ende"               # Ende = letzter Teil


def test_add_scene_after_and_at_end():
    p = run([{"op": "add_scene", "chapter_id": A, "title": "Neu1", "after_scene_id": S1},
             {"op": "add_scene", "chapter_id": A, "title": "Neu2"},
             {"op": "add_scene", "chapter_id": A, "title": "Neu0", "after_scene_id": ""}])
    ids = {s["title"]: s["id"] for s in p.new_scenes}
    assert _order(p.structure)[0][1] == [ids["Neu0"], S1, ids["Neu1"], S2, ids["Neu2"]]


def test_placeholders_refer_to_new_chapters_and_scenes():
    p = run([{"op": "add_chapter", "title": "K", "scenes": [{"title": "s1"}]},
             {"op": "add_scene", "chapter_id": "new:1", "title": "s2", "after_scene_id": "new:1"},
             {"op": "rename_chapter", "chapter_id": "new:1", "title": "K!"},
             {"op": "move_scene", "scene_id": S1, "chapter_id": "new:1", "after_scene_id": "new:2"}])
    order = _order(p.structure)
    new = {s["title"]: s["id"] for s in p.new_scenes}
    assert order[-1] == ("K!", [new["s1"], new["s2"], S1]) and order[0] == ("Eins", [S2])
    assert p.ids == {"chapters": {"new:1": p.structure["parts"][1]["chapters"][-1]["id"]},
                     "scenes": {"new:1": new["s1"], "new:2": new["s2"]}}


def test_delete_chapter_and_scene_collect_deletions():
    p = run([{"op": "delete_scene", "scene_id": S2}, {"op": "delete_chapter", "chapter_id": B}])
    assert _order(p.structure) == [("Eins", [S1]), ("Drei", [S4])]
    assert p.deleted_scenes == [S2] and [c["id"] for c in p.deleted_chapters] == [B]
    assert p.deleted_chapters[0]["scenes"] == [S3] and p.deleted_chapters[0]["place"] == {"part_id": P1, "after": A}


def test_delete_last_scene_takes_chapter_and_empty_part_disappears():
    p = run([{"op": "delete_scene", "scene_id": S4}])
    assert [pt["id"] for pt in p.structure["parts"]] == [P1]
    assert [c["id"] for c in p.deleted_chapters] == [C] and p.deleted_scenes == []


def test_last_chapter_of_the_book_stays():
    fails([{"op": "delete_chapter", "chapter_id": A}, {"op": "delete_chapter", "chapter_id": B},
           {"op": "delete_chapter", "chapter_id": C}], "last_chapter", step=3)


def test_new_scene_deleted_again_is_just_dropped():
    p = run([{"op": "add_scene", "chapter_id": A, "title": "weg"}, {"op": "delete_scene", "scene_id": "new:1"}])
    assert p.new_scenes == [] and p.deleted_scenes == [] and _order(p.structure)[0][1] == [S1, S2]


def test_new_chapter_deleted_again_is_just_dropped():
    p = run([{"op": "add_chapter", "title": "K", "scenes": [{"title": "s"}]}, {"op": "delete_chapter", "chapter_id": "new:1"}])
    assert p.new_scenes == [] and p.deleted_chapters == [] and len(_order(p.structure)) == 3


def test_move_scene_across_chapters_and_to_start():
    p = run([{"op": "move_scene", "scene_id": S2, "chapter_id": C},
             {"op": "move_scene", "scene_id": S3, "chapter_id": A, "after_scene_id": ""},
             {"op": "delete_chapter", "chapter_id": B}])
    assert _order(p.structure) == [("Eins", [S3, S1]), ("Drei", [S4, S2])]
    assert p.deleted_chapters == [{"id": B, "title": "Zwei", "scenes": [], "place": {"part_id": P1, "after": A}}]


def test_chapter_left_empty_by_moves_is_an_error_unless_deleted():
    e = fails([{"op": "move_scene", "scene_id": S3, "chapter_id": A}], "chapter_empty")
    assert e.detail["title"] == "Zwei"


def test_move_scene_after_itself_or_unknown_target_fails():
    fails([{"op": "move_scene", "scene_id": S1, "chapter_id": A, "after_scene_id": S1}], "after_invalid", step=1)
    fails([{"op": "move_scene", "scene_id": S1, "chapter_id": A, "after_scene_id": S4}], "after_invalid", step=1)


def test_move_chapter_within_and_across_parts():
    p = run([{"op": "move_chapter", "chapter_id": A, "after_chapter_id": B}])
    assert [t for t, _ in _order(p.structure)] == ["Zwei", "Eins", "Drei"]
    p = run([{"op": "move_chapter", "chapter_id": C, "after_chapter_id": ""}])
    assert [t for t, _ in _order(p.structure)] == ["Drei", "Eins", "Zwei"] and len(p.structure["parts"]) == 1
    p = run([{"op": "move_chapter", "chapter_id": A, "after_chapter_id": C}])
    assert p.structure["parts"][1]["chapters"][-1]["id"] == A


def test_set_chapter_summary_also_for_new_chapter():
    p = run([{"op": "set_chapter_summary", "chapter_id": A, "summary": " Kurz. "},
             {"op": "add_chapter", "title": "K", "scenes": [{"title": "s"}]},
             {"op": "set_chapter_summary", "chapter_id": "new:1", "summary": "Neu."}])
    new_cid = p.ids["chapters"]["new:1"]
    assert p.summaries == {A: "Kurz.", new_cid: "Neu."}


def test_summary_of_deleted_chapter_is_dropped():
    p = run([{"op": "set_chapter_summary", "chapter_id": B, "summary": "X"}, {"op": "delete_chapter", "chapter_id": B}])
    assert p.summaries == {}


@pytest.mark.parametrize("steps, code", [
    ([], "steps_invalid"),
    ("x", "steps_invalid"),
    ([{"op": "explode"}], "op_invalid"),
    ([{"op": "rename_chapter", "chapter_id": "f" * 32, "title": "x"}], "chapter_not_found"),
    ([{"op": "rename_chapter", "chapter_id": A, "title": " "}], "title_invalid"),
    ([{"op": "rename_chapter", "chapter_id": A, "title": "x" * 201}], "title_invalid"),
    ([{"op": "delete_scene", "scene_id": "9" * 32}], "scene_not_found"),
    ([{"op": "add_scene", "chapter_id": "new:1", "title": "x"}], "chapter_not_found"),
    ([{"op": "add_chapter", "title": "K", "scenes": []}], "scenes_invalid"),
    ([{"op": "add_chapter", "title": "K", "scenes": [{"title": "s", "summary": "x" * 2001}]}], "summary_invalid"),
    ([{"op": "add_chapter", "title": "K", "after_chapter_id": "f" * 32, "scenes": [{"title": "s"}]}], "after_invalid"),
    ([{"op": "set_chapter_summary", "chapter_id": A, "summary": "x" * 4001}], "summary_invalid"),
    ([{"op": "move_chapter", "chapter_id": A, "after_chapter_id": A}], "after_invalid"),
    ([{"op": "rename_chapter", "chapter_id": "../x", "title": "x"}], "chapter_not_found"),
])
def test_invalid_steps_are_rejected_with_step_number(steps, code):
    fails(steps, code, step=1 if isinstance(steps, list) and steps else None)


def test_error_in_later_step_names_that_step():
    e = fails([{"op": "rename_chapter", "chapter_id": A, "title": "ok"}, {"op": "delete_scene", "scene_id": "9" * 32}],
              "scene_not_found", step=2)
    assert e.detail["op"] == "delete_scene"


def test_too_many_steps_and_scene_limit():
    fails([{"op": "rename_chapter", "chapter_id": A, "title": "x"}] * (MAX_STEPS + 1), "steps_invalid")
    with pytest.raises(StoryError) as e:
        run([{"op": "add_scene", "chapter_id": A, "title": "x"}] * 3, max_scenes=6)
    assert e.value.code == "too_many_scenes" and e.value.detail["step"] == 3


def test_items_name_things_and_describe_gives_readable_lines():
    steps = [{"op": "rename_chapter", "chapter_id": B, "title": "Neu"}, {"op": "delete_scene", "scene_id": S2},
             {"op": "add_scene", "chapter_id": A, "title": "Frisch"},
             {"op": "move_scene", "scene_id": S1, "chapter_id": C}, {"op": "delete_chapter", "chapter_id": A},
             {"op": "add_chapter", "title": "K", "scenes": [{"title": "s"}, {"title": "t"}]},
             {"op": "move_chapter", "chapter_id": "new:1", "after_chapter_id": ""},
             {"op": "set_chapter_summary", "chapter_id": C, "summary": "Z."}]
    p = run(steps, titles={S1: "Hafen", S2: "Brief", S3: "Nacht", S4: "Ende"})
    assert p.items[0] == {"op": "rename_chapter", "name": "Neu", "old": "Zwei"}
    assert p.items[1] == {"op": "delete_scene", "name": "Brief", "chapter": "Eins"}
    assert p.items[3] == {"op": "move_scene", "name": "Hafen", "chapter": "Drei"}
    assert p.items[4] == {"op": "delete_chapter", "name": "Eins", "count": 1}   # die neue „Frisch“ ist noch drin
    assert describe(p.items, fiction=True) == [
        "Kapitel „Zwei“ umbenennen in „Neu“", "Szene „Brief“ löschen (Papierkorb)", "Neue Szene „Frisch“ in „Eins“",
        "Szene „Hafen“ verschieben nach „Drei“", "Kapitel „Eins“ mit 1 Szene(n) löschen (Papierkorb)",
        "Neues Kapitel „K“ mit 2 Szene(n)", "Kapitel „K“ verschieben", "Kapitel-Zusammenfassung für „Drei“ setzen"]
    assert describe(p.items, fiction=False)[1] == "Abschnitt „Brief“ löschen (Papierkorb)"


def test_new_scene_in_deleted_chapter_is_not_sent_to_trash():
    """Neue Szene ins Kapitel B, dann B löschen: in den Papierkorb nur die alten Szenen – die neue gibt es noch nicht."""
    p = run([{"op": "add_scene", "chapter_id": B, "title": "neu"}, {"op": "delete_chapter", "chapter_id": B}])
    assert p.deleted_chapters[0]["scenes"] == [S3] and p.new_scenes == []
