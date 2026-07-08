from __future__ import annotations

from unittest.mock import patch

import pytest

from backend import characters, storage, video
from conftest import PROJECT_ID


# ---- Fix 1: kein 0-Byte-Frame in der Galerie, wenn ffmpeg fehlschlägt --------

@pytest.mark.asyncio
async def test_continuation_frame_cleans_up_on_ffmpeg_failure():
    src = storage.videos_dir(PROJECT_ID) / "clip.mp4"
    src.write_bytes(b"fake-video")
    video_rel = f"videos/{src.name}"

    async def boom(_video, _out):
        raise RuntimeError("ffmpeg exploded")

    with patch("backend._ffmpeg.extract_last_frame", side_effect=boom):
        with pytest.raises(RuntimeError):
            await video.extract_continuation_frame(PROJECT_ID, video_rel)

    # Keine leeren Bild-/Sidecar-Leichen in images/
    leftovers = list(storage.images_dir(PROJECT_ID).glob("*"))
    assert leftovers == []


@pytest.mark.asyncio
async def test_continuation_frame_success_writes_image_and_sidecar():
    src = storage.videos_dir(PROJECT_ID) / "clip.mp4"
    src.write_bytes(b"fake-video")
    video_rel = f"videos/{src.name}"

    async def fake_extract(_video, out_jpg):
        out_jpg.write_bytes(b"jpeg-bytes")

    with patch("backend._ffmpeg.extract_last_frame", side_effect=fake_extract):
        rel = await video.extract_continuation_frame(PROJECT_ID, video_rel)

    assert rel is not None and rel.startswith("images/")
    img = storage.atelier_root(PROJECT_ID) / rel
    assert img.read_bytes() == b"jpeg-bytes"
    assert img.with_suffix(img.suffix + ".json").is_file()


# ---- Fix 2: remove_reference löscht nur innerhalb characters/ ----------------

def test_remove_reference_does_not_delete_outside_characters_dir():
    char = characters.create_character(PROJECT_ID, {"name": "Hero"})
    cid = char["id"]

    # Eine Galerie-Datei, die NICHT im characters/-Baum liegt.
    victim = storage.images_dir(PROJECT_ID) / "keep_me.png"
    victim.write_bytes(b"important")
    outside_rel = f"images/{victim.name}"

    # Referenz zeigt (künstlich) auf die Galerie-Datei.
    characters.add_reference(PROJECT_ID, cid, outside_rel)

    result = characters.remove_reference(PROJECT_ID, cid, outside_rel)

    # Referenz aus der Figur entfernt …
    assert result is not None
    assert outside_rel not in (result.get("references") or [])
    # … aber die fremde Galerie-Datei bleibt erhalten.
    assert victim.is_file()


def test_remove_reference_deletes_file_inside_characters_dir():
    char = characters.create_character(PROJECT_ID, {"name": "Hero"})
    cid = char["id"]

    rel = storage.save_reference_bytes(PROJECT_ID, cid, b"ref", ext="png")
    characters.add_reference(PROJECT_ID, cid, rel)
    ref_path = storage.atelier_root(PROJECT_ID) / rel
    assert ref_path.is_file()

    result = characters.remove_reference(PROJECT_ID, cid, rel)

    assert result is not None
    assert rel not in (result.get("references") or [])
    assert not ref_path.exists()
