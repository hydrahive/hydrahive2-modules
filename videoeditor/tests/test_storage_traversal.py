"""Path-Traversal-Schutz in storage.py — Pfade müssen innerhalb des
videoeditor-Roots des Projekts bleiben."""
from __future__ import annotations

import pytest

from backend import storage

PROJECT_ID = "test-project-videoeditor"


def test_original_path_stays_inside_root():
    p = storage.original_path(PROJECT_ID, "a" * 32, "mp4")
    root = storage._root(PROJECT_ID).resolve()
    assert p.resolve().is_relative_to(root)


def test_safe_path_rejects_traversal_in_filename():
    with pytest.raises(ValueError):
        storage._safe_path(PROJECT_ID, "originals", "../../etc/passwd")


def test_video_ext_from_rejects_unknown_extension():
    assert storage.video_ext_from("movie.mp4") == "mp4"
    assert storage.video_ext_from("movie.exe") is None
    assert storage.video_ext_from("no-extension") is None


def test_new_id_is_valid_hex32():
    fid = storage.new_id()
    assert storage.is_valid_id(fid)


def test_is_project_id_rejects_bad_chars():
    assert storage.is_project_id("valid-project-123")
    assert not storage.is_project_id("../etc")
    assert not storage.is_project_id("a")  # zu kurz
