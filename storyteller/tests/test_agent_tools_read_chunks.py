"""T1a (Task 29fb3911): lange Szenen in Abschnitten lesen – nichts geht verloren, Schnitt an Wort-/Absatzgrenze."""
from __future__ import annotations

from pathlib import Path

from backend import storage
from backend.agent_tools import TOOLS, read
from conftest import PROJECT_ID

READ = next(t for t in TOOLS if t.name == "storyteller_read")


def _ctx():
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id="testuser", workspace=Path("/tmp"), project_id=PROJECT_ID)


def _scene(text: str):
    b = storage.create_book(PROJECT_ID, {"title": "Lang", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": text}, base_version=1)
    return b["id"], sid


async def _all_chunks(bid, sid):
    parts, offset, calls = [], 0, 0
    while offset is not None:
        res = await READ.execute({"book_id": bid, "scene_ids": [sid], "offset": offset}, _ctx())
        assert res.success, res.error
        s = res.output["scenes"][0]
        parts.append(s["text"])
        assert s["offset"] == offset
        offset = s["next_offset"]
        calls += 1
        assert calls < 50
    return parts, s


async def test_chunks_together_give_the_whole_scene(monkeypatch):
    monkeypatch.setattr(read, "MAX_TEXT", 40)
    text = "Erster Absatz mit einigen Wörtern.\n\nZweiter Absatz, etwas länger als der erste.\n\nDritter und letzter Absatz."
    bid, sid = _scene(text)
    parts, last = await _all_chunks(bid, sid)
    assert "".join(parts) == text and len(parts) > 1
    assert last["cut"] is False and last["next_offset"] is None and last["total_chars"] == len(text)


async def test_cut_prefers_paragraph_end(monkeypatch):
    monkeypatch.setattr(read, "MAX_TEXT", 40)
    bid, sid = _scene("Ein ganzer Absatz hier.\n\nZweiter Absatz mit mehr Wörtern darin.")
    parts, _ = await _all_chunks(bid, sid)
    assert parts[0] == "Ein ganzer Absatz hier.\n\n"              # Absatzende inkl. Leerzeile, nicht mitten drin


async def test_cut_falls_on_word_boundary_not_mid_word(monkeypatch):
    monkeypatch.setattr(read, "MAX_TEXT", 25)
    bid, sid = _scene("Wort " * 30)
    parts, _ = await _all_chunks(bid, sid)
    assert all(p.endswith(" ") for p in parts[:-1])          # nie mitten im Wort abgeschnitten


async def test_first_read_without_offset_tells_how_to_continue(monkeypatch):
    monkeypatch.setattr(read, "MAX_TEXT", 20)
    bid, sid = _scene("Mia stand am Kai. " * 5)
    res = await READ.execute({"book_id": bid, "scene_ids": [sid]}, _ctx())
    s = res.output["scenes"][0]
    assert s["cut"] is True and s["offset"] == 0 and 0 < s["next_offset"] <= 20
    assert "offset" in res.output["hint"]                      # Agent erfährt, wie er weiterliest


async def test_word_without_any_space_is_cut_hard_and_still_complete(monkeypatch):
    monkeypatch.setattr(read, "MAX_TEXT", 10)
    bid, sid = _scene("x" * 35)
    parts, _ = await _all_chunks(bid, sid)
    assert "".join(parts) == "x" * 35


async def test_offset_needs_exactly_one_scene_and_valid_range():
    bid, sid = _scene("kurz")
    two = await READ.execute({"book_id": bid, "scene_ids": [sid, sid], "offset": 0}, _ctx())
    assert not two.success and "eine Szene" in two.error
    for bad in (-1, 4, 5, "x", True):          # 4 = Länge von „kurz“: hinter dem Ende
        res = await READ.execute({"book_id": bid, "scene_ids": [sid], "offset": bad}, _ctx())
        assert not res.success, bad


async def test_short_scene_has_no_next_offset_and_no_hint():
    bid, sid = _scene("Kurze Szene.")
    res = await READ.execute({"book_id": bid, "scene_ids": [sid]}, _ctx())
    s = res.output["scenes"][0]
    assert s["cut"] is False and s["next_offset"] is None and "hint" not in res.output


def test_schema_documents_offset():
    props = READ.schema["properties"]
    assert props["offset"]["type"] == "integer" and "next_offset" in props["offset"]["description"]
