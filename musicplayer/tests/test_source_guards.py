"""Jede Schutzregel des Quellen-Scanners für sich (Fehler-Injektion 02.10.2026).

Im Gesamtablauf fangen sich die Regeln gegenseitig ab (z. B. scheitert
`../x` schon an der Quellenliste). Hier wird jede Regel einzeln an
`safe_source_file` / `source_metadata` geprüft, damit sie nicht unbemerkt
entfallen kann.
"""
from __future__ import annotations

import json
import os

import pytest
from _hh_isolation import remove_test_tree
from conftest import PROJECT_A

VIDEO = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


@pytest.fixture
def root(client):
    from backend import storage

    r = storage.project_workspace(PROJECT_A)
    yield r
    for relative in ("atelier", "generated", "outside-target"):
        d = r / relative
        if d.exists():
            remove_test_tree(d)


def test_endung_muss_zur_quelle_passen(root):
    """atelier/videos ist eine Video-Quelle: eine .mp3 dort wird nicht angeboten."""
    from backend import sources

    d = root / "atelier" / "videos"
    d.mkdir(parents=True)
    (d / "falsch.mp3").write_bytes(b"ID3" + b"\x00" * 32)
    (d / "fremd.mov").write_bytes(VIDEO)
    assert sources.safe_source_file(PROJECT_A, "atelier/videos/falsch.mp3") is None
    assert sources.safe_source_file(PROJECT_A, "atelier/videos/fremd.mov") is None


def test_punkt_punkt_im_pfad_wird_abgelehnt(root):
    """Auch innerhalb einer gültigen Quelle: generated/../generated/x.mp4."""
    from backend import sources

    (root / "generated").mkdir(parents=True)
    (root / "generated" / "x.mp4").write_bytes(VIDEO)
    assert sources.safe_source_file(PROJECT_A, "generated/../generated/x.mp4") is None
    assert sources.safe_source_file(PROJECT_A, "generated/./x.mp4") is None


def test_quellordner_als_symlink_nach_aussen_wird_abgelehnt(root, tmp_path):
    """generated/<unterordner> zeigt per Symlink aus dem Workspace heraus."""
    from backend import sources

    outside = tmp_path / "draussen"
    outside.mkdir()
    (outside / "geheim.mp4").write_bytes(VIDEO)
    (root / "generated").mkdir(parents=True)
    os.symlink(outside, root / "generated" / "sub")
    assert sources.safe_source_file(PROJECT_A, "generated/sub/geheim.mp4") is None
    assert all("geheim" not in e["path"] for e in sources.list_sources(PROJECT_A))


def test_aufgeloester_pfad_ausserhalb_wird_abgelehnt(root, tmp_path, monkeypatch):
    """Workspace-Grenze für sich: auch wenn die Symlink-Prüfung nichts findet
    (z. B. Bind-Mount), darf ein Ziel außerhalb nicht durchgehen."""
    from backend import sources

    outside = tmp_path / "bind"
    outside.mkdir()
    (outside / "x.mp4").write_bytes(VIDEO)
    (root / "generated").mkdir(parents=True)
    os.symlink(outside / "x.mp4", root / "generated" / "x.mp4")
    monkeypatch.setattr(sources, "_has_symlink", lambda *_: False)
    assert sources.safe_source_file(PROJECT_A, "generated/x.mp4") is None


def test_zu_grosses_sidecar_wird_ignoriert(tmp_path):
    from backend import source_metadata

    (tmp_path / "a.json").write_text(json.dumps({"prompt": "x" * 70_000, "video_rel": "a.mp4"}))
    by_stem, by_file = source_metadata.load(tmp_path)
    assert by_stem == {} and by_file == {}
