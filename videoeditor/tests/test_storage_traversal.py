"""Path-Traversal-Schutz in storage.py.

Zwei Schutz-Bereiche:
1. source_path(): Originale liegen IRGENDWO im Projekt-Workspace (kein Silo) —
   der Pfad muss trotzdem innerhalb des Workspace-Roots bleiben.
2. _cache_path(): Editor-eigene Cache-Dateien (Proxy/Sprite/Meta/Export) bleiben
   innerhalb von <workspace>/videoeditor/.
"""
from __future__ import annotations

import pytest

from backend import storage

PROJECT_ID = "test-project-videoeditor"


def test_proxy_path_stays_inside_editor_cache():
    p = storage.proxy_path(PROJECT_ID, "a" * 32)
    root = storage._editor_root(PROJECT_ID).resolve()
    assert p.resolve().is_relative_to(root)


def test_cache_path_rejects_traversal_in_filename():
    with pytest.raises(ValueError):
        storage._cache_path(PROJECT_ID, "proxies", "../../etc/passwd")


def test_source_path_allows_nested_workspace_paths():
    """Originale dürfen überall im Workspace liegen (z.B. atelier/videos/x.mp4)."""
    p = storage.source_path(PROJECT_ID, "atelier/videos/clip.mp4")
    root = storage.workspace_root(PROJECT_ID).resolve()
    assert p is not None
    assert p.resolve().is_relative_to(root)


def test_source_path_rejects_traversal():
    assert storage.source_path(PROJECT_ID, "../../etc/passwd") is None
    assert storage.source_path(PROJECT_ID, "/etc/passwd") is None
    assert storage.source_path(PROJECT_ID, "a/../../b") is None


def test_source_path_rejects_empty():
    assert storage.source_path(PROJECT_ID, "") is None


def test_file_id_for_is_stable_hash():
    a = storage.file_id_for("atelier/videos/clip.mp4")
    b = storage.file_id_for("atelier/videos/clip.mp4")
    c = storage.file_id_for("atelier/videos/other.mp4")
    assert a == b
    assert a != c
    assert storage.is_valid_id(a)


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
