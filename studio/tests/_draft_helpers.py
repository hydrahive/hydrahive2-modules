"""Hilfen für die B2-Tests: Testbuch im Storyteller-Format (nur Dateien, kein Storyteller-Modul) und Pfade."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"
D = f"{P}/draft"


def _id() -> str:
    return uuid.uuid4().hex


def make_book(ws: Path, *, title: str = "Der Leuchtturm", chapters: list[dict] | None = None,
              entities: list[dict] | None = None) -> dict:
    """Legt ein Buch an. chapters: [{"title": .., "scenes": [{"title", "summary", "pov"}]}]. Gibt IDs zurück."""
    bid = _id()
    d = ws / "storyteller" / "books" / bid
    (d / "scenes").mkdir(parents=True)
    out = {"id": bid, "chapters": [], "entities": []}
    chs = []
    for ch in chapters if chapters is not None else [
        {"title": "Ankunft", "scenes": [{"title": "Am Steg", "summary": "Mira wartet am Steg auf das Boot.", "pov": "Mira"},
                                        {"title": "", "summary": ""}]},
        {"title": "Sturm", "scenes": [{"title": "Die Nacht", "summary": "Der Sturm trifft den Leuchtturm.", "pov": "Ole"}]},
    ]:
        cid, sids = _id(), []
        for sc in ch["scenes"]:
            sid = _id()
            sids.append(sid)
            (d / "scenes" / f"{sid}.json").write_text(json.dumps({"id": sid, "version": 1, **sc}))
            (d / "scenes" / f"{sid}.md").write_text("Text, der nicht übernommen wird.")
        chs.append({"id": cid, "title": ch["title"], "scenes": sids})
        out["chapters"].append({"id": cid, "scenes": sids})
    ents = []
    for e in entities if entities is not None else [
        {"kind": "character", "name": "Mira", "aliases": ["Miri"], "description": "Junge Wärterin im roten Mantel.",
         "fields": [{"key": "Augenfarbe", "value": "grün"}]},
        {"kind": "place", "name": "Leuchtturm", "aliases": [], "description": "Weißer Turm auf den Klippen.", "fields": []},
        {"kind": "item", "name": "Laterne", "aliases": [], "description": "", "fields": []},
    ]:
        eid = _id()
        ents.append({"id": eid, **e})
        out["entities"].append(eid)
    (d / "structure.json").write_text(json.dumps({"parts": [{"id": _id(), "title": "Teil 1", "chapters": chs}], "entities": ents}))
    (d / "book.json").write_text(json.dumps({"id": bid, "title": title, "kind": "novel", "version": 1}))
    return out
