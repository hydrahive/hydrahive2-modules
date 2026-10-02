"""Import beliebiger erlaubter Projektmedien in die Bibliothek."""
from __future__ import annotations

import json

import pytest
from _hh_isolation import remove_test_tree
from conftest import PROJECT_A, PROJECT_B

PREFIX = "/api/modules/musicplayer"
VIDEO = b"\x00\x00\x00\x18ftypmp42video"


def _base(project_id: str = PROJECT_A) -> str:
    return f"{PREFIX}/projects/{project_id}"


@pytest.fixture
def video_source():
    from backend import storage

    root = storage.project_workspace(PROJECT_A)
    directory = root / "atelier" / "videos"
    directory.mkdir(parents=True, exist_ok=True)
    video = directory / "scene.mp4"
    video.write_bytes(VIDEO)
    (directory / "job.json").write_text(json.dumps({
        "video_rel": "videos/scene.mp4", "prompt": "Szene am Meer",
        "model": "veo-fast", "duration": 5,
        "created_at": "2026-10-02T10:00:00Z",
    }))
    yield "atelier/videos/scene.mp4"
    remove_test_tree(root / "atelier")
    media = root / "media"
    if media.exists():
        remove_test_tree(media)


def test_videoimport_kopiert_mit_art_endung_und_meta(client, writer_headers, video_source):
    from backend import storage, tracks_store

    response = client.post(
        f"{_base()}/sources/import", json={"path": video_source}, headers=writer_headers,
    )
    assert response.status_code == 201

    track = tracks_store.get(PROJECT_A, response.json()["id"])
    assert track["media_kind"] == "video"
    assert track["ext"] == "mp4"
    assert json.loads(track["meta"])["prompt"] == "Szene am Meer"
    assert track["filename"].endswith(".mp4")
    stored = storage.file_path(PROJECT_A, track["filename"])
    assert stored is not None and stored.parent == storage.video_dir(PROJECT_A)
    assert stored.read_bytes() == VIDEO

    public = client.get(f"{_base()}/tracks", headers=writer_headers).json()["tracks"][0]
    assert public["media_kind"] == "video"
    assert public["ext"] == "mp4"
    assert public["meta"]["model"] == "veo-fast"


def test_videoimport_dedup_409_auch_ueber_alias(client, writer_headers, video_source):
    payload = {"path": video_source}
    first = client.post(f"{_base()}/generated/import", json=payload, headers=writer_headers)
    second = client.post(f"{_base()}/sources/import", json=payload, headers=writer_headers)
    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.parametrize("path", [
    "atelier/audio/profiles/hidden.mp3",
    "generated/one/two/hidden.mp3",
    "generated/rejected.mov",
    "../other/generated/escape.mp3",
    "atelier/videos/link.mp4",
])
def test_import_blockiert_ungueltige_quellen(client, writer_headers, path):
    from backend import storage

    root = storage.project_workspace(PROJECT_A)
    target = root / path if not path.startswith("..") else None
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.endswith("link.mp4"):
            inside = root / "symlink-target.mp4"
            inside.write_bytes(VIDEO)
            target.symlink_to(inside)
        else:
            target.write_bytes(VIDEO)
    try:
        response = client.post(
            f"{_base()}/sources/import", json={"path": path}, headers=writer_headers,
        )
        assert response.status_code == 404
    finally:
        for relative in ("atelier", "generated"):
            directory = root / relative
            if directory.exists():
                remove_test_tree(directory)
        (root / "symlink-target.mp4").unlink(missing_ok=True)


def test_import_aus_fremdem_projekt_bleibt_unerreichbar(client, writer_headers):
    from backend import storage

    foreign = storage.project_workspace(PROJECT_B) / "generated" / "foreign.mp4"
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_bytes(VIDEO)
    try:
        response = client.post(
            f"{_base()}/sources/import",
            json={"path": f"../{PROJECT_B}/generated/foreign.mp4"},
            headers=writer_headers,
        )
        assert response.status_code == 404
    finally:
        remove_test_tree(foreign.parent)
