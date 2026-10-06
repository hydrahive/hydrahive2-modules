"""Ghostwriter G1: Material für eine Szene, Modellwahl ohne festes Modell, Schreiben in Abschnitten."""
from __future__ import annotations

import asyncio
import pathlib
import re

import pytest
from conftest import PROJECT_ID

from backend import ghost, storage
from backend.storage import StoryError


def _book_with_scenes():
    b = storage.create_book(PROJECT_ID, {"title": "Die Verwandlung", "kind": "novel", "language": "de",
                                         "audience": "Erwachsene", "idea": "Ein Reisender wird zum Käfer."})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]["id"]
    s1 = st["parts"][0]["chapters"][0]["scenes"][0]
    s2 = storage.add_scene(PROJECT_ID, b["id"], ch, title="Der Prokurist")["scene"]["id"]
    s3 = storage.add_scene(PROJECT_ID, b["id"], ch, title="Hinaus")["scene"]["id"]
    storage.save_scene(PROJECT_ID, b["id"], s1, {"title": "Erwachen", "summary": "Gregor erwacht als Käfer.",
                                                 "text": "Anfang. " * 50 + "ENDE-EINS"}, base_version=1)
    storage.save_scene(PROJECT_ID, b["id"], s2, {"summary": "Der Prokurist kommt.", "pov": "Gregor"}, base_version=1)
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [
        {"id": "a" * 32, "kind": "character", "name": "Gregor", "aliases": ["Samsa"], "description": "Reisender", "fields": []},
        {"id": "b" * 32, "kind": "character", "name": "Der Prokurist", "aliases": ["Prokurist"], "description": "Chef", "fields": []},
        {"id": "c" * 32, "kind": "place", "name": "Bahnhof", "aliases": [], "description": "kommt nirgends vor", "fields": []},
    ]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    return b, s1, s2, s3


# ---------------------------------------------------------------- Material
def test_material_contains_everything_the_scene_needs():
    b, s1, s2, _ = _book_with_scenes()
    m = ghost.build_material(PROJECT_ID, b["id"], s2)
    user = m.prompt
    assert "Ein Reisender wird zum Käfer." in user and "Erwachsene" in user
    assert "Erwachen: Gregor erwacht als Käfer." in user           # Gedächtnis
    assert "ENDE-EINS" in user                                       # Ende der vorigen Szene
    assert "Der Prokurist kommt." in user and "Gregor" in user       # Szene + Perspektive
    assert "Reisender" in user and "Chef" in user                    # Steckbriefe aus Gedächtnis/Szene
    assert "kommt nirgends vor" not in user                          # unbeteiligter Steckbrief nicht
    assert m.mode == "fill" and m.scene_id == s2


def test_material_scene_with_text_becomes_proposal_and_missing_summary_fails():
    b, s1, _, s3 = _book_with_scenes()
    assert ghost.build_material(PROJECT_ID, b["id"], s1).mode == "proposal"
    with pytest.raises(StoryError) as exc:
        ghost.build_material(PROJECT_ID, b["id"], s3)
    assert exc.value.code == "summary_required"


def test_memory_is_bounded_and_keeps_the_most_recent():
    b, s1, s2, _ = _book_with_scenes()
    long = "x" * 5000
    storage.save_scene(PROJECT_ID, b["id"], s1, {"summary": "ALT " + long[:1900]}, base_version=storage.get_scene(PROJECT_ID, b["id"], s1)["version"])
    m = ghost.build_material(PROJECT_ID, b["id"], s2, memory_chars=300)
    mem = m.prompt.split("BISHER GESCHAH:")[1].split("\n\n")[0]
    assert len(mem) <= 400


def test_system_prompt_rules():
    b, _, s2, _ = _book_with_scenes()
    sys_text = ghost.build_material(PROJECT_ID, b["id"], s2).system
    for must in ("deutsch", "keine überschrift", "nicht zitieren", "steckbriefe"):
        assert must in sys_text.lower(), must


def test_style_from_settings_goes_into_prompt():
    b, _, s2, _ = _book_with_scenes()
    storage.update_book(PROJECT_ID, b["id"], {"ghost": {"style": "Präsens, kurze Sätze"}}, base_version=storage.get_book(PROJECT_ID, b["id"])["version"])
    assert "Präsens, kurze Sätze" in ghost.build_material(PROJECT_ID, b["id"], s2).prompt


# ---------------------------------------------------------------- Modellwahl
def test_model_choice_ghost_then_book_then_none():
    assert ghost.choose_model({"model": "buch/m", "ghost": {"model": "ghost/m"}}, None) == "ghost/m"
    assert ghost.choose_model({"model": "buch/m", "ghost": {"model": ""}}, None) == "buch/m"
    assert ghost.choose_model({"model": "", "ghost": {"model": ""}}, None) is None      # Kern-Standard
    assert ghost.choose_model({"model": "buch/m", "ghost": {"model": "ghost/m"}}, "anfrage/m") == "anfrage/m"


def test_no_provider_or_model_name_hardcoded():
    """Till 06.10.: kein festes Modell im Code."""
    src = pathlib.Path(ghost.__file__).read_text(encoding="utf-8").lower()
    for name in ("claude", "sonnet", "haiku", "opus", "gpt-", "gemini", "minimax", "codex", "llama", "mistral"):
        assert name not in src, name


def test_lengths_from_settings_or_request_never_hardcoded_model():
    book = {"ghost": {"length_words": 0, "chunk_words": 0}}
    with pytest.raises(StoryError):
        ghost.plan_lengths(book, None)                                 # nichts gesetzt, nichts angefragt
    assert ghost.plan_lengths({"ghost": {"length_words": 1500, "chunk_words": 600}}, None) == (1500, 600)
    assert ghost.plan_lengths({"ghost": {"length_words": 1500, "chunk_words": 0}}, 800) == (800, 800)  # Abschnitt ≤ Länge
    assert ghost.plan_lengths({"ghost": {"length_words": 0, "chunk_words": 500}}, 2400) == (2400, 500)


# ---------------------------------------------------------------- Schreiben in Abschnitten
def _fake_stream(chunks: list[str], seen: list):
    async def fake(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.append({"messages": messages, "model": model, "max_tokens": max_tokens})
        text = chunks[min(len(seen) - 1, len(chunks) - 1)]
        for part in re.findall(r"\S+\s*", text):
            yield part
    return fake


def _collect(gen):
    async def run():
        return "".join([t async for t in gen])
    return asyncio.run(run())


def _words(n, word="wort"):
    return " ".join([word] * n) + "."


def test_writes_in_sections_until_length_reached(monkeypatch):
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    monkeypatch.setattr(ghost, "stream", _fake_stream([_words(300), _words(300), _words(300), _words(300)], seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)
    text = _collect(ghost.write_scene(m, model="test/m", length_words=900, chunk_words=300))
    assert len(seen) == 3                                          # 3 × 300 ≥ 85 % von 900
    assert len(text.split()) >= 900 * 0.85
    assert all(c["model"] == "test/m" for c in seen)
    assert "SO WEIT GESCHRIEBEN" in seen[1]["messages"][1]["content"]  # Folgeabschnitt kennt Text davor


def test_stops_after_max_sections_even_if_short(monkeypatch):
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    monkeypatch.setattr(ghost, "stream", _fake_stream([_words(50)], seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)
    _collect(ghost.write_scene(m, model=None, length_words=6000, chunk_words=2000))
    assert len(seen) == ghost.MAX_SECTIONS


def test_heading_and_preamble_removed_per_section(monkeypatch):
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    monkeypatch.setattr(ghost, "stream", _fake_stream(["# Szene 2\n\nHier ist die Szene:\n" + _words(300), "## Fortsetzung\n\n" + _words(300)], seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)
    text = _collect(ghost.write_scene(m, model=None, length_words=500, chunk_words=300))
    assert "#" not in text and "Hier ist" not in text and "Fortsetzung" not in text


def test_closing_the_generator_stops_without_further_calls(monkeypatch):
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    monkeypatch.setattr(ghost, "stream", _fake_stream([_words(300)] * 4, seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)

    async def run():
        gen = ghost.write_scene(m, model=None, length_words=1200, chunk_words=300)
        got = []
        async for t in gen:
            got.append(t)
            if len(got) == 3:
                break
        await gen.aclose()
        return got
    asyncio.run(run())
    assert len(seen) == 1


def test_max_tokens_follows_chunk_size(monkeypatch):
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    monkeypatch.setattr(ghost, "stream", _fake_stream([_words(2000)], seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)
    _collect(ghost.write_scene(m, model=None, length_words=2000, chunk_words=2000))
    assert seen[0]["max_tokens"] >= 2000 * 2   # deutsch ≈ 1,5–2 Tokens je Wort, mit Luft


def test_streams_piece_by_piece_after_head_and_keeps_spacing(monkeypatch):
    """Nach dem Anfangspuffer kommen die Stücke einzeln (live); Leerzeichen zwischen Stücken bleiben."""
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    monkeypatch.setattr(ghost, "stream", _fake_stream([_words(300)], seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)

    async def run():
        return [t async for t in ghost.write_scene(m, model=None, length_words=300, chunk_words=300)]
    pieces = asyncio.run(run())
    assert len(pieces) > 100                                   # nicht alles auf einmal
    assert len(pieces[0]) <= ghost._HEAD_BUFFER + 20           # erster Teil = Anfangspuffer
    assert "".join(pieces) == _words(300)                      # nichts verloren, Abstände stimmen
