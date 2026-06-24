"""Storage-Helfer — Validierung + Traversal-Schutz."""
from __future__ import annotations

from backend import storage


def test_is_allowed_upload():
    assert storage.is_allowed_upload("song.mp3", "audio/mpeg")
    assert storage.is_allowed_upload("SONG.MP3", "audio/mp3")
    assert storage.is_allowed_upload("song.mp3", None)  # MIME unbekannt → ok wenn Endung passt
    assert not storage.is_allowed_upload("bild.png", "image/png")
    assert not storage.is_allowed_upload("song.mp3", "image/png")
    assert not storage.is_allowed_upload("noext", "audio/mpeg")


def test_save_und_path_roundtrip():
    name = storage.save_bytes(b"hello-audio")
    assert name.endswith(".mp3")
    p = storage.file_path(name)
    assert p is not None and p.read_bytes() == b"hello-audio"
    storage.delete_file(name)
    assert storage.file_path(name) is None


def test_file_path_blockt_traversal():
    assert storage.file_path("../../etc/passwd") is None
    assert storage.file_path("foo/bar.mp3") is None
    assert storage.file_path("..\\windows.mp3") is None


def test_uuid_namen_eindeutig():
    a = storage.save_bytes(b"a")
    b = storage.save_bytes(b"b")
    assert a != b
    storage.delete_file(a)
    storage.delete_file(b)
