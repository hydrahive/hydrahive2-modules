from __future__ import annotations

import json
import re

from backend import service, storage
from conftest import PROJECT_ID


def test_save_image_bytes_uses_images_dir_and_readable_name():
    rel = storage.save_image_bytes(
        PROJECT_ID,
        b"fake-image",
        ext="png",
        prompt="A dramatic castle at sunset!",
    )

    assert rel.startswith("images/")
    name = rel.removeprefix("images/")
    assert re.match(r"^\d{8}_a_dramatic_castle_at_sunset_[a-f0-9]{8}\.png$", name)
    assert (storage.images_dir(PROJECT_ID) / name).read_bytes() == b"fake-image"


def test_scan_gallery_reads_new_images_and_legacy_output():
    new_rel = storage.save_image_bytes(PROJECT_ID, b"new", ext="jpg", prompt="New image")
    new_name = new_rel.removeprefix("images/")
    (storage.images_dir(PROJECT_ID) / f"{new_name}.json").write_text(
        json.dumps({"prompt": "new prompt", "created_at": "2026-07-08T00:00:00Z"}),
        "utf-8",
    )

    legacy = storage.output_dir(PROJECT_ID) / "legacy.png"
    legacy.write_bytes(b"legacy")
    legacy.with_suffix(".png.json").write_text(json.dumps({"prompt": "legacy prompt"}), "utf-8")

    rels = {item["rel"]: item for item in service.scan_gallery(PROJECT_ID)}

    assert new_rel in rels
    assert rels[new_rel]["prompt"] == "new prompt"
    assert "output/legacy.png" in rels
    assert rels["output/legacy.png"]["prompt"] == "legacy prompt"


def test_delete_gallery_image_allows_images_and_legacy_output():
    new_rel = storage.save_image_bytes(PROJECT_ID, b"new", ext="png", prompt="Delete me")
    new_path = storage.atelier_root(PROJECT_ID) / new_rel
    new_path.with_suffix(".png.json").write_text("{}", "utf-8")

    legacy = storage.output_dir(PROJECT_ID) / "legacy.png"
    legacy.write_bytes(b"legacy")
    legacy.with_suffix(".png.json").write_text("{}", "utf-8")

    assert service.delete_gallery_image(PROJECT_ID, new_rel) is True
    assert not new_path.exists()
    assert not new_path.with_suffix(".png.json").exists()

    assert service.delete_gallery_image(PROJECT_ID, "output/legacy.png") is True
    assert not legacy.exists()
    assert not legacy.with_suffix(".png.json").exists()
