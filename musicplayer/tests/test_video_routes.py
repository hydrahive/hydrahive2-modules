"""Video-Upload, Medienfilter, MIME, Downloadendung und Range-Streaming."""
from __future__ import annotations

import io

import pytest
from conftest import PROJECT_A

PREFIX = "/api/modules/musicplayer"
MP3 = b"ID3audio-bytes"
WEBM = b"\x1aE\xdf\xa3webm-video-bytes"


def _base() -> str:
    return f"{PREFIX}/projects/{PROJECT_A}"


def _upload(client, headers, name: str, data: bytes, mime: str):
    return client.post(
        f"{_base()}/tracks",
        files={"file": (name, io.BytesIO(data), mime)},
        headers=headers,
    )


def test_webm_upload_landet_im_videoordner_und_trackout_ist_vollstaendig(client, writer_headers):
    from backend import storage, tracks_store

    response = _upload(client, writer_headers, "movie.webm", WEBM, "application/octet-stream")
    assert response.status_code == 201
    stored = tracks_store.get(PROJECT_A, response.json()["id"])
    path = storage.file_path(PROJECT_A, stored["filename"])
    assert path is not None and path.parent == storage.video_dir(PROJECT_A)

    track = client.get(f"{_base()}/tracks", headers=writer_headers).json()["tracks"][0]
    assert track["media_kind"] == "video"
    assert track["ext"] == "webm"
    assert track["meta"] == {}


def test_trackliste_filtert_nach_kind(client, writer_headers):
    _upload(client, writer_headers, "song.mp3", MP3, "audio/mpeg")
    _upload(client, writer_headers, "movie.webm", WEBM, "video/webm")

    audio = client.get(f"{_base()}/tracks?kind=audio", headers=writer_headers).json()["tracks"]
    video = client.get(f"{_base()}/tracks?kind=video", headers=writer_headers).json()["tracks"]
    both = client.get(f"{_base()}/tracks", headers=writer_headers).json()["tracks"]
    assert [track["media_kind"] for track in audio] == ["audio"]
    assert [track["media_kind"] for track in video] == ["video"]
    assert {track["media_kind"] for track in both} == {"audio", "video"}


def test_upload_art_nur_aus_endung_und_mov_wird_abgelehnt(client, writer_headers):
    accepted = _upload(client, writer_headers, "song.ogg", b"ogg", "image/png")
    rejected = _upload(client, writer_headers, "movie.mov", b"mov", "video/quicktime")
    assert accepted.status_code == 201
    assert rejected.status_code == 400


def test_upload_limits_sind_50_mb_audio_und_60_mb_video(client, writer_headers, monkeypatch):
    from backend import routes

    assert routes.UPLOAD_LIMITS == {
        "audio": 50 * 1024 * 1024,
        "video": 60 * 1024 * 1024,
    }
    monkeypatch.setitem(routes.UPLOAD_LIMITS, "video", 8)
    response = _upload(client, writer_headers, "movie.mp4", b"123456789", "video/mp4")
    assert response.status_code == 413


@pytest.mark.parametrize(("extension", "expected_mime"), [
    ("mp3", "audio/mpeg"), ("wav", "audio/wav"), ("ogg", "audio/ogg"),
    ("m4a", "audio/mp4"), ("flac", "audio/flac"), ("mp4", "video/mp4"),
    ("webm", "video/webm"),
])
def test_stream_liefert_mime_aus_endung(client, writer_headers, reader_headers, extension, expected_mime):
    track_id = _upload(client, writer_headers, f"medium.{extension}", b"media", "ignored/type").json()["id"]
    response = client.get(f"{_base()}/tracks/{track_id}/stream", headers=reader_headers)
    assert response.headers["content-type"].startswith(expected_mime)


def test_stream_webm_mime_downloadendung_und_range_206(client, writer_headers, reader_headers):
    track_id = _upload(client, writer_headers, "movie.webm", WEBM, "video/webm").json()["id"]
    stream = client.get(
        f"{_base()}/tracks/{track_id}/stream",
        headers={**reader_headers, "Range": "bytes=0-3"},
    )
    download = client.get(
        f"{_base()}/tracks/{track_id}/stream?download=1", headers=reader_headers,
    )

    assert stream.status_code == 206
    assert stream.content == WEBM[:4]
    assert stream.headers["content-type"].startswith("video/webm")
    assert stream.headers["content-range"] == f"bytes 0-3/{len(WEBM)}"
    assert download.headers["content-disposition"].endswith('.webm"')
