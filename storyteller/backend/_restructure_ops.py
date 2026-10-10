"""C2 – die einzelnen Umbau-Schritte auf der Kopie der Gliederung (Teil von _restructure_plan.py).

Jede Funktion ändert ``run.p.structure`` und liefert einen Eintrag für die Anzeige ({op, name, …}). Leere Kapitel
(z. B. nach Verschieben) prüft ``plan`` am Ende – so darf ein Kapitel zwischendurch leer sein, solange es danach
gelöscht wird oder wieder Szenen bekommt.
"""
from __future__ import annotations

from typing import Any

from ._files import StoryError


def _rename_chapter(run, s: dict) -> dict:
    ch = run.chapter(run.ref(s.get("chapter_id"), "chapter"))
    old, ch["title"] = ch["title"], run.title(s.get("title"))
    return {"op": "rename_chapter", "name": ch["title"], "old": old}


def _add_chapter(run, s: dict) -> dict:
    scenes = s.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise StoryError("scenes_invalid")
    title = run.title(s.get("title"))
    if "after_chapter_id" in s and s["after_chapter_id"] != "":
        after = s["after_chapter_id"]
        try:
            target = run.ref(after, "chapter")
        except StoryError:
            raise StoryError("after_invalid") from None
        part = run.part_of(target)
        at = [c["id"] for c in part["chapters"]].index(target) + 1
    elif s.get("after_chapter_id") == "":
        part, at = run.parts[0], 0
    else:
        part = run.parts[-1]
        at = len(part["chapters"])
    cid = run.new_id()
    ids = [run.new_scene(x) for x in scenes]
    part["chapters"].insert(at, {"id": cid, "title": title, "scenes": ids})
    run.p.ids["chapters"][f"new:{len(run.p.ids['chapters']) + 1}"] = cid
    run.new_chapter_ids.add(cid)
    return {"op": "add_chapter", "name": title, "count": len(ids)}


def _add_scene(run, s: dict) -> dict:
    ch = run.chapter(run.ref(s.get("chapter_id"), "chapter"))
    at = run.insert_at(ch["scenes"], s.get("after_scene_id"), "scene")
    sid = run.new_scene({"title": s.get("title"), "summary": s.get("summary")})
    ch["scenes"].insert(at, sid)
    return {"op": "add_scene", "name": run.titles[sid], "chapter": ch["title"]}


def _delete_chapter(run, s: dict) -> dict:
    cid = run.ref(s.get("chapter_id"), "chapter")
    ch = run.chapter(cid)
    count = len(ch["scenes"])                     # alle, die mit dem Kapitel weggehen (auch eben erst neu angelegte)
    run.drop_chapter(cid)
    return {"op": "delete_chapter", "name": ch["title"], "count": count}


def _delete_scene(run, s: dict) -> dict:
    sid = run.ref(s.get("scene_id"), "scene")
    ch = run.chapter_of(sid)
    item = {"op": "delete_scene", "name": run.titles.get(sid, "…"), "chapter": ch["title"]}
    if len(ch["scenes"]) <= 1:                     # letzte Szene nimmt ihr Kapitel mit (wie C1)
        run.drop_chapter(ch["id"])
        return {**item, "with_chapter": True}
    ch["scenes"].remove(sid)
    if sid in run.new_scene_ids:
        run.p.new_scenes = [x for x in run.p.new_scenes if x["id"] != sid]
    else:
        run.p.deleted_scenes.append(sid)
    return item


def _move_scene(run, s: dict) -> dict:
    sid = run.ref(s.get("scene_id"), "scene")
    target = run.chapter(run.ref(s.get("chapter_id"), "chapter"))
    # Kopie: bei einem Fehler danach wird sie ohnehin verworfen. „Hinter sich selbst“ scheitert danach in insert_at
    # (die Szene steht dann nirgends mehr → after_invalid).
    run.chapter_of(sid)["scenes"].remove(sid)
    target["scenes"].insert(run.insert_at(target["scenes"], s.get("after_scene_id"), "scene"), sid)
    return {"op": "move_scene", "name": run.titles.get(sid, "…"), "chapter": target["title"]}


def _move_chapter(run, s: dict) -> dict:
    """after_chapter_id: fehlt = ans Ende des Buchs (letzter Teil), "" = an den Anfang des Buchs, sonst danach."""
    cid = run.ref(s.get("chapter_id"), "chapter")
    after = s.get("after_chapter_id")
    target = run.ref_or_none(after, "chapter") if after else None
    if after and (target is None or target == cid):
        raise StoryError("after_invalid")
    part = run.part_of(cid)
    ch = next(c for c in part["chapters"] if c["id"] == cid)
    part["chapters"].remove(ch)
    if target is not None:
        dest = run.part_of(target)
        at = [c["id"] for c in dest["chapters"]].index(target) + 1
    elif after == "":
        dest, at = run.parts[0], 0                # an den Anfang des Buchs
    else:
        dest = run.parts[-1]
        at = len(dest["chapters"])
    dest["chapters"].insert(at, ch)
    if not part["chapters"]:
        run.parts.remove(part)
    return {"op": "move_chapter", "name": ch["title"]}


def _set_chapter_summary(run, s: dict) -> dict:
    from ._restructure_plan import MAX_CHAPTER_SUMMARY
    cid = run.ref(s.get("chapter_id"), "chapter")
    run.p.summaries[cid] = run.text(s.get("summary"), MAX_CHAPTER_SUMMARY)
    return {"op": "set_chapter_summary", "name": run.chapter(cid)["title"]}


_OPS = {"rename_chapter": _rename_chapter, "add_chapter": _add_chapter, "add_scene": _add_scene,
        "delete_chapter": _delete_chapter, "delete_scene": _delete_scene, "move_scene": _move_scene,
        "move_chapter": _move_chapter, "set_chapter_summary": _set_chapter_summary}


def apply_step(run, op: str, step: dict[str, Any]) -> dict:
    return _OPS[op](run, step)
