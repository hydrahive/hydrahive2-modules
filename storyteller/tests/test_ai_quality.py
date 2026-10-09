"""A5(a): Prompts je Buchart, Gedächtnis an Zeilengrenzen, Umschreiben an der richtigen Stelle (Spec ki-qualitaet-a5.md)."""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import ai, ghost, storage
from backend._memory import MemoryIndex


def _book(kind, n=2):
    b = storage.create_book(PROJECT_ID, {"title": "B", "kind": kind, "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]
    ids = [ch["scenes"][0]]
    for i in range(1, n):
        ids.append(storage.add_scene(PROJECT_ID, b["id"], ch["id"], f"S{i}", after=ids[-1])["scene"]["id"])
    for i, sid in enumerate(ids):
        s = storage.get_scene(PROJECT_ID, b["id"], sid)
        storage.save_scene(PROJECT_ID, b["id"], sid, {"summary": f"Inhalt {i}.", "text": f"Text {i}."},
                           base_version=s["version"])
    return b["id"], ids


@pytest.mark.parametrize("kind", ["nonfiction", "learning"])
def test_non_fiction_prompt_speaks_of_sections_not_scenes(kind):
    bid, ids = _book(kind)
    m = ghost.build_material(PROJECT_ID, bid, ids[1])
    whole = m.system + m.prompt
    assert "Romantext" not in whole and "Szene" not in whole and "SZENE" not in whole
    assert ("Sachtext" if kind == "nonfiction" else "Lehrtext") in m.system
    assert "EINEN Abschnitt" in m.system and "DIESER ABSCHNITT" in m.prompt
    assert "ENDE DES VORIGEN ABSCHNITTS" in m.prompt


def test_novel_prompt_still_speaks_of_scenes():
    bid, ids = _book("novel")
    m = ghost.build_material(PROJECT_ID, bid, ids[1])
    assert "Romantext" in m.system and "EINE Szene" in m.system and "DIESE SZENE" in m.prompt


async def test_sections_of_a_non_fiction_text_are_called_parts(monkeypatch):
    bid, ids = _book("nonfiction")
    seen = []

    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.append(messages[-1]["content"])
        yield "Wort " * 120
    monkeypatch.setattr(ghost, "stream", fake_stream)
    m = ghost.build_material(PROJECT_ID, bid, ids[1])
    async for _ in ghost.write_scene(m, model=None, length_words=400, chunk_words=120):
        pass
    assert "Schreibe den Anfang dieses Abschnitts" in seen[0]
    assert "Schreibe den nächsten Teil dieses Abschnitts" in seen[1]
    assert "BISHERIGE TEILE DIESES ABSCHNITTS" in seen[2]
    assert not any("Szene" in s for s in seen)


async def test_summary_of_a_non_fiction_section(monkeypatch):
    bid, ids = _book("learning")
    s = storage.get_scene(PROJECT_ID, bid, ids[0])
    storage.save_scene(PROJECT_ID, bid, ids[0], {"summary": ""}, base_version=s["version"])
    seen = []

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.append(messages[0]["content"])
        return "Kurz."
    monkeypatch.setattr(ghost, "complete", fake_complete)
    await ghost.summarize_scene(PROJECT_ID, bid, ids[0])
    assert seen[0].startswith("Fasse den Abschnitt") and "Figuren" not in seen[0]


def test_editor_prompt_for_non_fiction():
    bid, ids = _book("nonfiction")
    _system, prompt = ai._context(PROJECT_ID, bid, ids[0], "", "continue")
    assert "Inhalt, Gedankengang und Ton" in prompt and "Handlung" not in prompt
    s = storage.get_scene(PROJECT_ID, bid, ids[0])
    storage.save_scene(PROJECT_ID, bid, ids[0], {"text": ""}, base_version=s["version"])
    _system, prompt = ai._context(PROJECT_ID, bid, ids[0], "", "continue")
    assert "Der Abschnitt beginnt hier." in prompt


# --- Gedächtnis an Zeilengrenzen ---------------------------------------------------------------------------------

def test_memory_is_cut_at_line_boundaries_only():
    bid, ids = _book("novel", n=12)
    idx = MemoryIndex.load(PROJECT_ID, bid)
    full = idx.memory(ids[-1], 10_000)
    lines = full.split("\n")
    for limit in range(len(lines[-1]), len(full) + 5, 7):
        got = idx.memory(ids[-1], limit)
        assert len(got) <= limit
        assert got == "" or got.split("\n") == lines[len(lines) - len(got.split("\n")):], limit


def test_memory_keeps_last_line_even_if_longer_than_limit():
    """Eine einzelne zu lange Zeile wird von vorn gekürzt (sonst wäre das Gedächtnis leer) – Anfang mit „…“."""
    bid, ids = _book("novel", n=3)
    s = storage.get_scene(PROJECT_ID, bid, ids[1])
    storage.save_scene(PROJECT_ID, bid, ids[1], {"summary": "x" * 500}, base_version=s["version"])
    got = MemoryIndex.load(PROJECT_ID, bid).memory(ids[2], 100)
    assert got.startswith("…") and len(got) <= 100 and got.endswith("x")


# --- Umschreiben an der richtigen Stelle -------------------------------------------------------------------------

@pytest.mark.parametrize("text, sel, occ, want", [
    ("a X b X c", "X", 0, 2), ("a X b X c", "X", 1, 6), ("a X b X c", "X", None, 6),
    ("a X b X c", "X", 5, 6), ("a X b", "Y", 0, -1), ("abc", "", 0, -1), ("XX", "X", 1, 1),
])
def test_find_selection(text, sel, occ, want):
    assert ai.find_selection(text, sel, occ) == want


def test_rewrite_gets_context_of_the_marked_occurrence():
    bid, ids = _book("novel")
    s = storage.get_scene(PROJECT_ID, bid, ids[0])
    storage.save_scene(PROJECT_ID, bid, ids[0], {"text": "ANFANG. Es regnete. MITTE. Es regnete. SCHLUSS."},
                       base_version=s["version"])
    _s, first = ai._context(PROJECT_ID, bid, ids[0], "Es regnete.", "rewrite", occurrence=0)
    assert "Text davor:\nANFANG. " in first and "Text danach:\n MITTE. Es regnete. SCHLUSS." in first
    _s, last = ai._context(PROJECT_ID, bid, ids[0], "Es regnete.", "rewrite")
    assert "Text danach:\n SCHLUSS." in last


def test_suggest_route_passes_occurrence(client, auth_headers, monkeypatch):
    got = {}

    async def fake(user, pid, bid, sid, action, selection, model, occurrence=None):
        got["occ"] = occurrence
        return {"proposal": "x", "model": ""}
    monkeypatch.setattr(ai, "suggest", fake)
    bid, ids = _book("novel")
    url = f"{MOD_PREFIX}/projects/{PROJECT_ID}/books/{bid}/ai/suggest"
    r = client.post(url, json={"scene_id": ids[0], "action": "rewrite", "selection": "x", "occurrence": 3},
                    headers=auth_headers)
    assert r.status_code == 200 and got["occ"] == 3
    r = client.post(url, json={"scene_id": ids[0], "action": "rewrite", "selection": "x", "occurrence": -1},
                    headers=auth_headers)
    assert r.status_code == 422
