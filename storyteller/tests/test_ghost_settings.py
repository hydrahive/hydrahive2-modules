"""Ghostwriter G1: Einstellungen je Buch (book.json: ghost) und Herkunft je Szene (origin).

Grundsatz (Till, 06.10.): kein festes Modell und keine festen Werte im Code – alles je Buch einstellbar.
"""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import importer, storage
from backend.storage import StoryError

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book():
    return storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})


def _first_scene(b):
    return storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]


# ---------------------------------------------------------------- Einstellungen
def test_new_book_has_empty_ghost_settings():
    b = _book()
    assert b["ghost"] == {"model": "", "length_words": 0, "chunk_words": 0, "style": "", "limit_tokens": 0}


def test_update_ghost_settings_and_version():
    b = _book()
    g = {"model": "irgendein/modell", "length_words": 1500, "chunk_words": 600, "style": "knapp, Präsens",
         "limit_tokens": 50_000}
    nb = storage.update_book(PROJECT_ID, b["id"], {"ghost": g}, base_version=b["version"])
    assert nb["ghost"] == g and nb["version"] == b["version"] + 1
    # Teilweise ändern: nicht genannte Felder bleiben
    nb2 = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"style": ""}}, base_version=nb["version"])
    assert nb2["ghost"] == {**g, "style": ""}


@pytest.mark.parametrize("bad", [
    {"model": 3}, {"model": "x" * 201}, {"length_words": 100}, {"length_words": 6001}, {"length_words": "1500"},
    {"chunk_words": 199}, {"chunk_words": 2001}, {"style": "x" * 2001}, {"unbekannt": 1}, "kein dict",
    {"length_words": True}, {"limit_tokens": 999}, {"limit_tokens": 20_000_001}, {"limit_tokens": -1},
    {"limit_tokens": True}, {"limit_tokens": 1.5},
])
def test_ghost_settings_are_validated(bad):
    b = _book()
    with pytest.raises(StoryError):
        storage.update_book(PROJECT_ID, b["id"], {"ghost": bad}, base_version=b["version"])
    assert storage.get_book(PROJECT_ID, b["id"])["version"] == b["version"]


def test_zero_means_not_set():
    """0 = nicht gesetzt (Oberfläche zeigt dann ihre Auswahl); 200–6000 sonst."""
    b = _book()
    nb = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"length_words": 0, "chunk_words": 0}}, base_version=b["version"])
    assert nb["ghost"]["length_words"] == 0


def test_limit_tokens_zero_means_no_limit_and_range():
    """Kostengrenze je Auftrag (Spec kostengrenze.md §3): 0 = aus, sonst 1.000–20.000.000 Tokens (Eingabe + Ausgabe)."""
    b = _book()
    nb = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"limit_tokens": 1000}}, base_version=b["version"])
    nb = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"limit_tokens": 20_000_000}}, base_version=nb["version"])
    assert nb["ghost"]["limit_tokens"] == 20_000_000
    nb = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"limit_tokens": 0}}, base_version=nb["version"])
    assert nb["ghost"]["limit_tokens"] == 0


def test_old_book_without_ghost_is_read_with_defaults():
    b = _book()
    d = storage.book_dir(PROJECT_ID, b["id"])
    import json
    raw = json.loads((d / "book.json").read_text())
    raw.pop("ghost")
    (d / "book.json").write_text(json.dumps(raw))
    assert storage.get_book(PROJECT_ID, b["id"])["ghost"]["model"] == ""


def test_http_patch_ghost(client, auth_headers):
    b = client.post(f"{P}/books", json={"title": "H", "kind": "novel"}, headers=auth_headers).json()
    r = client.patch(f"{P}/books/{b['id']}", json={"ghost": {"model": "a/b", "length_words": 800}, "base_version": b["version"]}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["ghost"]["length_words"] == 800
    r = client.patch(f"{P}/books/{b['id']}", json={"ghost": {"length_words": 5}, "base_version": r.json()["version"]}, headers=auth_headers)
    assert r.status_code == 400


# ---------------------------------------------------------------- Herkunft
def test_new_scene_is_human():
    b = _book()
    assert storage.get_scene(PROJECT_ID, b["id"], _first_scene(b))["origin"] == "human"


def test_origin_ai_draft_then_human_edit_becomes_ai_edited():
    b = _book()
    sid = _first_scene(b)
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "KI-Text", "origin": "ai_draft"}, base_version=1)
    assert s["origin"] == "ai_draft"
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"title": "Neu"}, base_version=s["version"])
    assert s["origin"] == "ai_draft"            # nur Titel geändert: Text bleibt KI-Entwurf
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "KI-Text, vom Menschen geändert"}, base_version=s["version"])
    assert s["origin"] == "ai_edited"
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "weiter"}, base_version=s["version"])
    assert s["origin"] == "ai_edited"            # bleibt bearbeitet


def test_human_scene_stays_human_on_edit_and_invalid_origin_rejected():
    b = _book()
    sid = _first_scene(b)
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "eigener Text"}, base_version=1)
    assert s["origin"] == "human"
    for bad in ("robot", "", 1):
        with pytest.raises(StoryError):
            storage.save_scene(PROJECT_ID, b["id"], sid, {"origin": bad}, base_version=s["version"])


def test_old_scene_without_origin_reads_as_human():
    b = _book()
    sid = _first_scene(b)
    import json
    meta_path = storage.book_dir(PROJECT_ID, b["id"]) / "scenes" / f"{sid}.json"
    meta = json.loads(meta_path.read_text())
    meta.pop("origin", None)
    meta_path.write_text(json.dumps(meta))
    assert storage.get_scene(PROJECT_ID, b["id"], sid)["origin"] == "human"


def test_import_keeps_valid_origin_and_defaults_others():
    data = {"title": "I", "kind": "novel", "language": "de", "parts": [{"title": "T", "chapters": [{"title": "K", "scenes": [
        {"title": "a", "text": "x", "origin": "ai_draft"}, {"title": "b", "text": "y", "origin": "quatsch"}, {"title": "c", "text": "z"}]}]}]}
    b = importer.import_book(PROJECT_ID, data)
    ids = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"]
    assert [storage.get_scene(PROJECT_ID, b["id"], s)["origin"] for s in ids] == ["ai_draft", "human", "human"]
    assert storage.get_book(PROJECT_ID, b["id"])["ghost"]["model"] == ""


def test_status_change_on_ai_draft_keeps_origin():
    """Nur Stand/Zusammenfassung ändern (Text gleich) macht aus dem KI-Entwurf keinen bearbeiteten."""
    b = _book()
    sid = _first_scene(b)
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "KI", "origin": "ai_draft"}, base_version=1)
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"status": "done", "summary": "x", "text": "KI"}, base_version=s["version"])
    assert s["origin"] == "ai_draft"
