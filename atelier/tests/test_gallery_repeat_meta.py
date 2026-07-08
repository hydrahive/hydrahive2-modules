"""Atelier — scan_gallery reicht die Sidecar-Felder für 'Wiederholen' durch."""
from __future__ import annotations

import json

from backend import service, storage
from conftest import PROJECT_ID


def test_scan_gallery_exposes_repeat_fields():
    rel = storage.save_image_bytes(PROJECT_ID, b"img", ext="png", prompt="A castle")
    name = rel.removeprefix("images/")
    sidecar = {
        "prompt": "A castle",
        "scene": "A castle on a hill",
        "character_ids": ["c1", "c2"],
        "seed": 42,
        "model": "google/gemini-2.5-flash-image",
        "aspect_ratio": "16:9",
        "camera": {"angle": "low"},
        "style": "cinematic",
        "created_at": "2026-07-08T00:00:00Z",
    }
    (storage.images_dir(PROJECT_ID) / f"{name}.json").write_text(json.dumps(sidecar), "utf-8")

    item = next(i for i in service.scan_gallery(PROJECT_ID) if i["rel"] == rel)

    assert item["scene"] == "A castle on a hill"
    assert item["character_ids"] == ["c1", "c2"]
    assert item["aspect_ratio"] == "16:9"
    assert item["camera"] == {"angle": "low"}
    assert item["style"] == "cinematic"


def test_scan_gallery_repeat_fields_default_empty():
    """Ohne Sidecar-Felder liefert die Galerie sichere Defaults (kein KeyError)."""
    storage.save_image_bytes(PROJECT_ID, b"img2", ext="png", prompt="Bare")

    items = service.scan_gallery(PROJECT_ID)
    assert items, "Galerie sollte das eben gespeicherte Bild enthalten"
    for it in items:
        assert it["character_ids"] == []
        assert it["camera"] == {}
        assert it["scene"] in (None, "")
        assert it["style"] in (None, "")
        assert it["aspect_ratio"] in (None, "")
