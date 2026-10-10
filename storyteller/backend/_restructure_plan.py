"""C2 – Gliederungs-Umbau planen: Schritte prüfen und auf einer KOPIE der Gliederung anwenden (Spec autor-gliederung-c2.md).

Reine Logik ohne Dateien: ``plan`` liefert die neue Gliederung und was beim Ausführen zu tun ist (neue Szenen anlegen,
Gelöschtes in den Papierkorb, Kapitel-Zusammenfassungen). Fehler → StoryError mit ``detail = {step, op}``; die Eingabe
bleibt unverändert. Neue Kapitel/Szenen sind in späteren Schritten als ``new:<n>`` ansprechbar (je Art gezählt).
"""
from __future__ import annotations

import copy
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ._files import StoryError

MAX_STEPS = 50
MAX_SUMMARY = 2000          # Szenen-Zusammenfassung (wie scenes._SCENE_FIELDS)
MAX_CHAPTER_SUMMARY = 4000  # wie chapter_summaries.MAX_SUMMARY
OPS = ("rename_chapter", "add_chapter", "add_scene", "delete_chapter", "delete_scene", "move_scene", "move_chapter",
       "set_chapter_summary")
_NEW = re.compile(r"^new:([1-9]\d{0,2})$")


@dataclass
class Plan:
    structure: dict
    new_scenes: list[dict] = field(default_factory=list)       # {id, title, summary}
    deleted_scenes: list[str] = field(default_factory=list)    # einzeln gelöscht (Kapitel bleibt)
    deleted_chapters: list[dict] = field(default_factory=list)  # {id, title, scenes, place}
    summaries: dict[str, str] = field(default_factory=dict)     # Kapitel-ID → Kapitel-Zusammenfassung
    ids: dict[str, dict[str, str]] = field(default_factory=lambda: {"chapters": {}, "scenes": {}})
    items: list[dict] = field(default_factory=list)             # je Schritt: was passiert (für Klartext/Antwort)


class _Run:
    def __init__(self, st: dict, new_id: Callable[[], str], titles: dict[str, str], max_scenes: int):
        self.p = Plan(structure=copy.deepcopy(st))
        self.new_id, self.titles, self.max_scenes = new_id, dict(titles), max_scenes
        self.new_scene_ids: set[str] = set()
        self.new_chapter_ids: set[str] = set()

    # --- Nachschlagen -------------------------------------------------------------------------------------------
    @property
    def parts(self) -> list[dict]:
        return self.p.structure["parts"]

    def chapters(self) -> list[dict]:
        return [c for pt in self.parts for c in pt["chapters"]]

    def ref(self, value: Any, kind: str) -> str:
        """Echte ID oder Platzhalter new:<n> → ID; unbekannt → <kind>_not_found."""
        if isinstance(value, str):
            m = _NEW.match(value)
            if m:
                value = self.p.ids["chapters" if kind == "chapter" else "scenes"].get(value, "")
        found = any(c["id"] == value for c in self.chapters()) if kind == "chapter" else \
            any(value in c["scenes"] for c in self.chapters())
        if not isinstance(value, str) or not found:
            raise StoryError(f"{kind}_not_found", 404)
        return value

    def ref_or_none(self, value: Any, kind: str) -> str | None:
        try:
            return self.ref(value, kind)
        except StoryError:
            return None

    def chapter(self, cid: str) -> dict:
        return next(c for c in self.chapters() if c["id"] == cid)

    def chapter_of(self, sid: str) -> dict:
        return next(c for c in self.chapters() if sid in c["scenes"])

    def part_of(self, cid: str) -> dict:
        return next(pt for pt in self.parts if any(c["id"] == cid for c in pt["chapters"]))

    def scene_count(self) -> int:
        return sum(len(c["scenes"]) for c in self.chapters())

    # --- Bausteine ----------------------------------------------------------------------------------------------
    @staticmethod
    def title(v: Any) -> str:
        if not isinstance(v, str) or not v.strip() or len(v) > 200:
            raise StoryError("title_invalid")
        return v.strip()

    @staticmethod
    def text(v: Any, limit: int) -> str:
        if v is None:
            return ""
        if not isinstance(v, str) or len(v) > limit:
            raise StoryError("summary_invalid")
        return v.strip()

    def new_scene(self, spec: Any) -> str:
        if not isinstance(spec, dict):
            raise StoryError("scenes_invalid")
        if self.scene_count() + 1 > self.max_scenes:
            raise StoryError("too_many_scenes")
        sid = self.new_id()
        self.p.new_scenes.append({"id": sid, "title": self.title(spec.get("title")),
                                  "summary": self.text(spec.get("summary"), MAX_SUMMARY)})
        self.p.ids["scenes"][f"new:{len(self.p.ids['scenes']) + 1}"] = sid
        self.new_scene_ids.add(sid)
        self.titles[sid] = self.p.new_scenes[-1]["title"]
        return sid

    def insert_at(self, items: list[str], after: Any, kind: str) -> int:
        """Position nach ``after`` (None = ans Ende, "" = an den Anfang)."""
        if after is None:
            return len(items)
        if after == "":
            return 0
        try:
            target = self.ref(after, kind)
        except StoryError:
            raise StoryError("after_invalid") from None
        if target not in items:
            raise StoryError("after_invalid")
        return items.index(target) + 1

    def drop_chapter(self, cid: str) -> dict:
        if len(self.chapters()) <= 1:
            raise StoryError("last_chapter", 409)
        part = self.part_of(cid)
        ids = [c["id"] for c in part["chapters"]]
        i = ids.index(cid)
        ch = part["chapters"].pop(i)
        if not part["chapters"]:
            self.parts.remove(part)
        self.p.summaries.pop(cid, None)
        gone = [s for s in ch["scenes"] if s not in self.new_scene_ids]
        self.p.new_scenes = [s for s in self.p.new_scenes if s["id"] not in ch["scenes"]]
        if cid in self.new_chapter_ids:
            return {"id": cid, "title": ch["title"], "scenes": [], "new": True}
        entry = {"id": cid, "title": ch["title"], "scenes": gone,
                 "place": {"part_id": part["id"], "after": ids[i - 1] if i else ""}}
        self.p.deleted_chapters.append(entry)
        return entry


from ._restructure_ops import apply_step


def plan(structure: dict, steps: Any, *, new_id: Callable[[], str], titles: dict[str, str] | None = None,
         max_scenes: int = 10_000) -> Plan:
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise StoryError("steps_invalid")
    run = _Run(structure, new_id, titles or {}, max_scenes)
    for n, step in enumerate(steps, start=1):
        op = step.get("op") if isinstance(step, dict) else None
        try:
            if op not in OPS:
                raise StoryError("op_invalid")
            run.p.items.append(apply_step(run, op, step))
        except StoryError as exc:
            raise StoryError(exc.code, exc.status, {**exc.detail, "step": n, "op": op}) from None
    for c in run.chapters():
        if not c["scenes"]:
            raise StoryError("chapter_empty", 400, {"chapter_id": c["id"], "title": c["title"]})
    return run.p


def describe(items: list[dict], *, fiction: bool) -> list[str]:
    from ._restructure_text import lines
    return lines(items, fiction=fiction)
