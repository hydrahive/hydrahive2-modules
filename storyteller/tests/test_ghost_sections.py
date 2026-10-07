"""Ghostwriter G1: Szene in Abschnitten schreiben (Länge, Vorspann, Abbruch, Wiederholungen). LLM gefälscht."""
from __future__ import annotations

import asyncio
import re

from conftest import PROJECT_ID

from backend import ghost, storage


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


def test_later_sections_know_the_whole_scene_not_only_the_tail(monkeypatch):
    """Befund hydratest 07.10. (2.500 Wörter): Modell sah nur die letzten 3.000 Zeichen und schrieb ein
    Gespräch aus Abschnitt 2 in Abschnitt 4 noch einmal. Folgeabschnitte bekommen deshalb auch eine
    Übersicht über ALLE bisherigen Abschnitte (Anfang jedes Abschnitts), mit der Bitte, nichts zu wiederholen."""
    b, _, s2, _ = _book_with_scenes()
    seen: list = []
    sec = [f"Abschnitt{i}anfang. " + _words(400, f"w{i}") for i in range(1, 5)]
    monkeypatch.setattr(ghost, "stream", _fake_stream(sec, seen))
    m = ghost.build_material(PROJECT_ID, b["id"], s2)
    _collect(ghost.write_scene(m, model="test/m", length_words=1600, chunk_words=400))
    last = seen[-1]["messages"][1]["content"]
    assert len(seen) == 4
    assert "Abschnitt1anfang" in last and "Abschnitt2anfang" in last          # früher Abschnitt sichtbar, obwohl > 3.000 Zeichen zurück
    assert "nicht wiederholen" in last.lower() or "nichts wiederholen" in last.lower()


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
