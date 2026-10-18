"""Studio B2: Entwurf aus dem Storyteller (studio/SPEC.md „Bauplan B2“). Nur lesen, nichts im Buch ändern."""
from __future__ import annotations

import hashlib

from _draft_helpers import D, make_book
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


def _sums(ws) -> dict:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ws / "storyteller").rglob("*") if p.is_file()}


def test_books_list(client, auth_headers, ws) -> None:
    assert client.get(f"{D}/books", headers=auth_headers).json() == {"books": []}
    b = make_book(ws)
    (ws / "storyteller" / "books" / "kaputt").mkdir()                                   # kein Buch → übersprungen
    books = client.get(f"{D}/books", headers=auth_headers).json()["books"]
    assert len(books) == 1 and books[0]["id"] == b["id"] and books[0]["title"] == "Der Leuchtturm"
    assert [c["title"] for c in books[0]["chapters"]] == ["Ankunft", "Sturm"]
    assert [c["scenes"] for c in books[0]["chapters"]] == [2, 1] and books[0]["entities"] == 3
    o = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/overview", headers=auth_headers).json()
    assert o["books"] == 1


def test_book_draft_mapping(client, auth_headers, ws) -> None:
    b = make_book(ws)
    before = _sums(ws)
    r = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"]})
    assert r.status_code == 200, r.text
    d, trunc = r.json()["draft"], r.json()["truncated"]
    assert trunc == 0 and d["head"]["title"] == "Der Leuchtturm"
    kinds = {e["name"]: e["kind"] for e in d["elements"]}
    assert kinds == {"Mira": "character", "Leuchtturm": "place", "Laterne": "object"}
    mira = next(e for e in d["elements"] if e["name"] == "Mira")
    assert "roten Mantel" in mira["description"] and "Augenfarbe: grün" in mira["description"]
    assert [s["title"] for s in d["scenes"]] == ["Am Steg", "Szene 2", "Die Nacht"]   # leerer Titel → „Szene N“
    first, last = d["scenes"][0], d["scenes"][2]
    assert first["description"] == "Mira wartet am Steg auf das Boot."
    assert first["element_keys"] == [mira["key"]]                                      # pov + Name im Text
    leuchtturm = next(e["key"] for e in d["elements"] if e["name"] == "Leuchtturm")
    assert last["element_keys"] == [leuchtturm]                                         # Name im Text; pov „Ole“ ohne Steckbrief
    assert all(s["shots"] == [] for s in d["scenes"])
    assert _sums(ws) == before                                                          # Buch unverändert


def test_alias_and_chapter_choice(client, auth_headers, ws) -> None:
    b = make_book(ws, chapters=[{"title": "A", "scenes": [{"title": "eins", "summary": "Miri lacht."}]},
                                {"title": "B", "scenes": [{"title": "zwei", "summary": ""}]}])
    d = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"], "chapter_ids": [b["chapters"][1]["id"]]}).json()["draft"]
    assert [s["title"] for s in d["scenes"]] == ["zwei"]
    d = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"], "chapter_ids": [b["chapters"][0]["id"]]}).json()["draft"]
    mira = next(e["key"] for e in d["elements"] if e["name"] == "Mira")
    assert d["scenes"][0]["element_keys"] == [mira]                                     # Alias „Miri“


def test_broken_scene_files_are_skipped(client, auth_headers, ws) -> None:
    b = make_book(ws)
    sid = b["chapters"][0]["scenes"][0]
    (ws / "storyteller" / "books" / b["id"] / "scenes" / f"{sid}.json").write_text("{kaputt")
    d = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"]}).json()["draft"]
    assert [s["title"] for s in d["scenes"]] == ["Szene 1", "Szene 2", "Die Nacht"]    # Szene bleibt, nur ohne Infos


def test_limit_200_scenes(client, auth_headers, ws) -> None:
    b = make_book(ws, chapters=[{"title": "lang", "scenes": [{"title": f"s{i}"} for i in range(205)]}], entities=[])
    r = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"]}).json()
    assert len(r["draft"]["scenes"]) == 200 and r["truncated"] == 5


def test_unknown_or_foreign_book(client, auth_headers, ws) -> None:
    for body in ({"book_id": "0" * 32}, {"book_id": "../x"}, {}):
        r = client.post(f"{D}/book", headers=auth_headers, json=body)
        assert r.status_code == 404 and r.json()["detail"]["code"] == "studio_book_not_found", body
    b = make_book(ws)
    r = client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/draft/book", headers=auth_headers, json={"book_id": b["id"]})
    assert r.status_code == 404


def test_pov_alone_assigns_the_character(client, auth_headers, ws) -> None:
    """Perspektive allein (Name kommt im Text nicht vor) ordnet die Figur zu, auch über einen Alias, ohne Groß/klein."""
    b = make_book(ws, chapters=[{"title": "A", "scenes": [{"title": "Nebel", "summary": "Niemand ist da.", "pov": "mira"},
                                                          {"title": "Wind", "summary": "Es pfeift.", "pov": "Miri"},
                                                          {"title": "Leer", "summary": "Stille.", "pov": "Ole"}]}])
    d = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"]}).json()["draft"]
    mira = next(e["key"] for e in d["elements"] if e["name"] == "Mira")
    assert [s["element_keys"] for s in d["scenes"]] == [[mira], [mira], []]


def test_german_endings_count_as_mention(client, auth_headers, ws) -> None:
    """„des Leuchtturms“, „Miras Mantel“ zählen als Erwähnung; „Lateinisch“ ist keine „Laterne“, „Miranda“ keine „Mira“."""
    b = make_book(ws, chapters=[{"title": "A", "scenes": [
        {"title": "Treppe", "summary": "Sie steigt die Treppe des Leuchtturms hinauf. Miras Mantel ist nass."},
        {"title": "Fremd", "summary": "Miranda spricht Lateinisch."}]}])
    d = client.post(f"{D}/book", headers=auth_headers, json={"book_id": b["id"]}).json()["draft"]
    key = {e["name"]: e["key"] for e in d["elements"]}
    assert sorted(d["scenes"][0]["element_keys"]) == sorted([key["Mira"], key["Leuchtturm"]])
    assert d["scenes"][1]["element_keys"] == []
