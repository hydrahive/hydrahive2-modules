"""Projektgebundener Storage — Validierung, Migration und Traversal-Schutz."""
from __future__ import annotations

from conftest import PROJECT_A, PROJECT_B
from backend import storage


def test_is_allowed_upload():
    assert storage.is_allowed_upload("song.mp3", "audio/mpeg")
    assert storage.is_allowed_upload("SONG.MP3", "audio/mp3")
    assert storage.is_allowed_upload("song.mp3", None)
    assert not storage.is_allowed_upload("bild.png", "image/png")
    assert not storage.is_allowed_upload("song.mp3", "image/png")
    assert not storage.is_allowed_upload("noext", "audio/mpeg")


def test_save_und_path_roundtrip_im_projektworkspace():
    name = storage.save_bytes(PROJECT_A, b"hello-audio")
    path = storage.file_path(PROJECT_A, name)

    assert path is not None
    assert path.read_bytes() == b"hello-audio"
    assert path.parent == storage.project_workspace(PROJECT_A) / "media" / "audio"
    assert storage.file_path(PROJECT_B, name) is None

    storage.delete_file(PROJECT_A, name)
    assert storage.file_path(PROJECT_A, name) is None


def test_file_path_blockt_traversal():
    assert storage.file_path(PROJECT_A, "../../etc/passwd") is None
    assert storage.file_path(PROJECT_A, "foo/bar.mp3") is None
    assert storage.file_path(PROJECT_A, "..\\windows.mp3") is None


def test_project_id_blockt_traversal():
    import pytest

    with pytest.raises(ValueError):
        storage.audio_dir("../../etc")


def test_audio_dir_folgt_keinem_media_symlink(tmp_path):
    import pytest

    outside = tmp_path / "outside"
    outside.mkdir()
    media = storage.project_workspace(PROJECT_A) / "media"
    if media.exists() and not media.is_symlink():
        import shutil
        shutil.rmtree(media)
    media.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match="symlink"):
            storage.audio_dir(PROJECT_A)
        assert not (outside / "audio").exists()
    finally:
        media.unlink(missing_ok=True)


def test_uuid_namen_eindeutig():
    first = storage.save_bytes(PROJECT_A, b"a")
    second = storage.save_bytes(PROJECT_A, b"b")
    assert first != second


def test_legacy_datei_wird_verifiziert_migriert_und_dann_entfernt():
    filename = "00000000-0000-4000-8000-000000000001.mp3"
    legacy = storage.legacy_storage_dir() / filename
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(b"legacy-audio")

    migrated = storage.file_path(PROJECT_A, filename, expected_size=len(b"legacy-audio"))

    assert migrated is not None and migrated.read_bytes() == b"legacy-audio"
    assert not legacy.exists()


def test_legacy_datei_bleibt_bei_falscher_erwarteter_groesse():
    filename = "00000000-0000-4000-8000-000000000002.mp3"
    legacy = storage.legacy_storage_dir() / filename
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(b"legacy-audio")

    assert storage.file_path(PROJECT_A, filename, expected_size=999) is None
    assert legacy.read_bytes() == b"legacy-audio"
