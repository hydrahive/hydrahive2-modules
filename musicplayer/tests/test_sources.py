"""Feste Projektquellen: Scan, Sidecars, Filter und Schutzregeln."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from _hh_isolation import remove_test_tree
from conftest import PROJECT_A

PREFIX = "/api/modules/musicplayer"


def _base() -> str:
    return f"{PREFIX}/projects/{PROJECT_A}"


def _write(root: Path, relative: str, data: bytes = b"media") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def source_tree(tmp_path):
    from backend import storage

    root = storage.project_workspace(PROJECT_A)
    paths = {
        "generated_mp3": _write(root, "generated/root.mp3"),
        "generated_wav": _write(root, "generated/agent/voice.wav"),
        "generated_mp4": _write(root, "generated/agent/clip.mp4"),
        "audio": _write(root, "atelier/audio/song.wav"),
        "broken": _write(root, "atelier/audio/broken.flac"),
        "missing": _write(root, "atelier/audio/missing.m4a"),
        "video": _write(root, "atelier/videos/rendered.mp4"),
        "film": _write(root, "atelier/films/final.mp4"),
        "media_audio": _write(root, "media/audio/reference.ogg"),
        "media_video": _write(root, "media/video/reference.webm"),
    }
    (root / "atelier/audio/song.json").write_text(json.dumps({
        "prompt": "Sommerregen", "model": "music-v1", "duration": 12.5,
        "created_at": "2026-10-01T10:00:00Z",
    }))
    (root / "atelier/audio/broken.json").write_text("{kaputt")
    (root / "atelier/videos/job.json").write_text(json.dumps({
        "video_rel": "videos/rendered.mp4", "prompt": "Ein Roboter winkt",
        "model": "veo", "duration": 4, "created_at": "2026-10-01T11:00:00Z",
    }))
    (root / "atelier/films/job.json").write_text(json.dumps({
        "film_rel": "films/final.mp4", "clips": ["videos/a.mp4"],
        "created_at": "2026-10-02T12:34:56Z",
    }))
    _write(root, "atelier/audio/profiles/hidden.mp3")
    _write(root, "generated/agent/deeper/hidden.mp3")
    _write(root, "generated/rejected.mov")

    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"outside")
    symlink = root / "generated/escape.mp3"
    symlink.symlink_to(outside)
    yield root, paths
    for relative in ("generated", "atelier", "media"):
        target = root / relative
        if target.exists() or target.is_symlink():
            remove_test_tree(target)


def test_sources_findet_feste_quellen_und_sidecar_metadaten(client, writer_headers, source_tree):
    response = client.get(f"{_base()}/sources", headers=writer_headers)

    assert response.status_code == 200
    rows = {row["path"]: row for row in response.json()}
    assert set(rows) == {
        "generated/root.mp3", "generated/agent/voice.wav", "generated/agent/clip.mp4",
        "atelier/audio/song.wav", "atelier/audio/broken.flac", "atelier/audio/missing.m4a",
        "atelier/videos/rendered.mp4", "atelier/films/final.mp4",
        "media/audio/reference.ogg", "media/video/reference.webm",
    }
    assert rows["atelier/audio/song.wav"]["title"] == "Sommerregen"
    assert rows["atelier/videos/rendered.mp4"]["meta"] == {
        "prompt": "Ein Roboter winkt", "model": "veo", "duration": 4,
        "created_at": "2026-10-01T11:00:00Z",
    }
    assert rows["atelier/films/final.mp4"]["title"] == "Film vom 2026-10-02T12:34:56Z"
    assert rows["atelier/audio/broken.flac"]["title"] == "broken.flac"
    assert rows["atelier/audio/missing.m4a"]["title"] == "missing.m4a"
    assert rows["generated/root.mp3"]["source"] == "generated"
    assert rows["atelier/videos/rendered.mp4"]["group"] == "Atelier · Szenen-Clips"


def test_sources_kind_filter_und_generated_alias(client, writer_headers, source_tree):
    videos = client.get(f"{_base()}/sources?kind=video", headers=writer_headers).json()
    alias = client.get(f"{_base()}/generated", headers=writer_headers).json()

    assert videos and {row["kind"] for row in videos} == {"video"}
    assert {row["path"] for row in alias} == {
        "generated/root.mp3", "generated/agent/voice.wav", "generated/agent/clip.mp4",
    }
    assert all("workspace" in row for row in alias)


def test_sources_ignoriert_bibliotheksdateien(client, writer_headers, source_tree):
    from backend import storage, tracks_store

    filename = storage.save_bytes(PROJECT_A, b"library", ext="mp3")
    tracks_store.add(
        PROJECT_A, title="Library", filename=filename, size_bytes=7,
        uploaded_by="writer", media_kind="audio", ext="mp3",
    )

    rows = client.get(f"{_base()}/sources", headers=writer_headers).json()
    assert f"media/audio/{filename}" not in {row["path"] for row in rows}


def test_sources_maximal_500_neueste(client, writer_headers):
    from backend import storage

    root = storage.project_workspace(PROJECT_A)
    generated = root / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    try:
        for index in range(505):
            path = _write(root, f"generated/{index:03}.mp3")
            os.utime(path, (index + 1, index + 1))
        rows = client.get(f"{_base()}/sources", headers=writer_headers).json()
        assert len(rows) == 500
        assert rows[0]["path"] == "generated/504.mp3"
        assert rows[-1]["path"] == "generated/005.mp3"
    finally:
        remove_test_tree(generated)


def test_sidecar_meta_ist_auf_zwei_kb_begrenzt(client, writer_headers):
    from backend import storage

    root = storage.project_workspace(PROJECT_A)
    audio = _write(root, "atelier/audio/long.mp3")
    audio.with_suffix(".json").write_text(json.dumps({
        "prompt": "ä" * 5000, "model": "m" * 1000, "created_at": "c" * 1000,
    }))
    try:
        row = client.get(f"{_base()}/sources", headers=writer_headers).json()[0]
        encoded = json.dumps(row["meta"], ensure_ascii=False, separators=(",", ":")).encode()
        assert len(encoded) <= 2048
    finally:
        remove_test_tree(root / "atelier")


def test_sources_braucht_schreibrecht(client, reader_headers):
    assert client.get(f"{_base()}/sources", headers=reader_headers).status_code == 403
