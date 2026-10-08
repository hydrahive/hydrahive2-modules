"""A4: Wortzahl in den Szenen-Infos – Bücherliste und Schätzung ohne Volltexte (Spec leistung-a4.md §2.3)."""
from __future__ import annotations

import json

from conftest import PROJECT_ID

from backend import storage


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "Zählbuch", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    return b["id"], sid


def _meta(bid, sid):
    return json.loads((storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.json").read_text())


def test_saving_a_scene_stores_its_word_count():
    bid, sid = _book()
    assert _meta(bid, sid)["words"] == 0
    storage.save_scene(PROJECT_ID, bid, sid, {"text": "Eins zwei drei – vier!"}, base_version=1)
    assert _meta(bid, sid)["words"] == 4                       # „–“ ist kein Wort
    assert storage.scene_info(PROJECT_ID, bid, sid)["words"] == 4
    assert "text" not in storage.scene_info(PROJECT_ID, bid, sid) and "text_sha" not in storage.scene_info(PROJECT_ID, bid, sid)


def test_list_books_sums_from_infos_without_reading_texts(monkeypatch):
    bid, sid = _book()
    storage.save_scene(PROJECT_ID, bid, sid, {"text": "Drei Wörter hier."}, base_version=1)
    from pathlib import Path
    orig = Path.read_text

    def no_md(self, *a, **k):
        assert not str(self).endswith(".md"), f"Volltext gelesen: {self}"
        return orig(self, *a, **k)
    monkeypatch.setattr(Path, "read_text", no_md)
    assert next(b for b in storage.list_books(PROJECT_ID) if b["id"] == bid)["words"] == 3


def test_old_scene_without_word_count_is_counted_from_text():
    """Szenen vor 0.17.0 haben kein „words“ → einmal aus dem Text zählen (keine Migration nötig)."""
    bid, sid = _book()
    storage.save_scene(PROJECT_ID, bid, sid, {"text": "Fünf Wörter in alter Szene."}, base_version=1)
    path = storage.book_dir(PROJECT_ID, bid) / "scenes" / f"{sid}.json"
    meta = json.loads(path.read_text())
    meta.pop("words")
    path.write_text(json.dumps(meta))
    assert next(b for b in storage.list_books(PROJECT_ID) if b["id"] == bid)["words"] == 5
    assert storage.scene_info(PROJECT_ID, bid, sid)["words"] == 5
