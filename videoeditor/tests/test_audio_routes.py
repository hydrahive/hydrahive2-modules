"""Audio-Nachvertonung-Routen: Guards, Browse, Prepare-Validierung.

ffmpeg wird NICHT aufgerufen (prepare startet nur den Job, wir prüfen den
Dispatch + die Validierung, nicht die tatsächliche Peaks-Erzeugung).
"""
from __future__ import annotations

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

from backend import storage


def _put_audio_file(rel: str, content: bytes = b"\x00" * 64) -> None:
    """Legt eine Datei im Projekt-Workspace ab (simuliert generierte Musik)."""
    dst = storage.workspace_root(PROJECT_ID) / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(content)


def _clear_workspace_audio() -> None:
    """Entfernt generated/-Testdateien früherer Tests (der Autouse-Fixture
    räumt nur videoeditor/, nicht den restlichen Workspace) — hält Browse-Tests
    reihenfolge-unabhängig."""
    gen = storage.workspace_root(PROJECT_ID) / "generated"
    if gen.is_dir():
        import shutil
        shutil.rmtree(gen)


def test_audio_browse_requires_auth(client):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/browse")
    assert r.status_code == 401


def test_audio_browse_foreign_project_404(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/audio/browse", headers=auth_headers)
    assert r.status_code == 404


def test_audio_browse_empty_initially(client, auth_headers):
    _clear_workspace_audio()
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/browse", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_audio_browse_lists_generated_files(client, auth_headers):
    _clear_workspace_audio()
    _put_audio_file("generated/song.mp3")
    _put_audio_file("generated/voice.wav")
    _put_audio_file("generated/ignore.txt")  # kein Audio
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/browse", headers=auth_headers)
    assert r.status_code == 200
    rels = {item["source_rel"] for item in r.json()}
    assert "generated/song.mp3" in rels
    assert "generated/voice.wav" in rels
    assert "generated/ignore.txt" not in rels
    for item in r.json():
        assert item["prepared"] is False  # noch nicht aufbereitet


def test_audio_browse_excludes_editor_cache(client, auth_headers):
    """Audiodateien im videoeditor/-Cache dürfen nicht als Quelle erscheinen."""
    _clear_workspace_audio()
    cache_mp3 = storage._editor_root(PROJECT_ID) / "exports" / "x.mp3"
    cache_mp3.parent.mkdir(parents=True, exist_ok=True)
    cache_mp3.write_bytes(b"\x00")
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/browse", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_prepare_rejects_unknown_source(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/prepare",
        headers=auth_headers, json={"source_rel": "generated/nope.mp3"},
    )
    assert r.status_code == 404


def test_prepare_rejects_traversal(client, auth_headers):
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/prepare",
        headers=auth_headers, json={"source_rel": "../../etc/passwd"},
    )
    assert r.status_code == 404


def test_prepare_rejects_non_audio_extension(client, auth_headers):
    _put_audio_file("generated/document.txt", b"hello")
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/prepare",
        headers=auth_headers, json={"source_rel": "generated/document.txt"},
    )
    assert r.status_code == 400


def test_prepare_starts_job_for_valid_audio(client, auth_headers):
    _put_audio_file("generated/track.mp3")
    r = client.post(
        f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/prepare",
        headers=auth_headers, json={"source_rel": "generated/track.mp3"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "audio_id" in body and "job_id" in body


def test_get_audio_meta_404_before_prepare(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/deadbeef", headers=auth_headers)
    assert r.status_code == 404


def test_get_audio_peaks_404_before_prepare(client, auth_headers):
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/audio/deadbeef/peaks", headers=auth_headers)
    assert r.status_code == 404
