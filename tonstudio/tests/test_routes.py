"""REST-Routen: Zugriff nur für Projektmitglieder, 409 bei Konflikt, Upload, Pfadschutz (SPEC.md §8)."""
from __future__ import annotations

import shutil
import subprocess

import pytest

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _tone(tmp_path) -> bytes:
    f = tmp_path / "t.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=1",
                    "-f", "mp3", str(f)], check=True)
    return f.read_bytes()


def test_ohne_login_kein_zugriff(client):
    assert client.get(f"{P}/songs").status_code == 401


def test_fremdes_projekt_ist_404(client, auth_headers, other_headers):
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/songs", headers=auth_headers).status_code == 404
    assert client.get(f"{P}/songs", headers=other_headers).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/..%2F..%2Fetc/songs", headers=auth_headers).status_code == 404


def test_song_anlegen_lesen_speichern_konflikt(client, auth_headers):
    r = client.post(f"{P}/songs", json={"title": "Die Klans V", "bpm": 132}, headers=auth_headers)
    assert r.status_code == 200
    song = r.json()
    sid = song["id"]
    assert client.get(f"{P}/songs/{sid}", headers=auth_headers).json()["bpm"] == 132
    r = client.put(f"{P}/songs/{sid}", json={**song, "key": "D minor", "expected_version": 1}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["version"] == 2
    r = client.put(f"{P}/songs/{sid}", json={**song, "key": "A minor", "expected_version": 1}, headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "version_conflict"
    assert r.json()["detail"]["params"]["current"] == 2


def test_song_ungueltige_daten_422(client, auth_headers):
    sid = client.post(f"{P}/songs", json={"title": "a"}, headers=auth_headers).json()["id"]
    bad = {"title": "a", "expected_version": 1,
           "tracks": [{"id": "t", "clips": [{"id": "c", "source_rel": "x.mp3", "src_start": 5, "src_end": 1}]}]}
    assert client.put(f"{P}/songs/{sid}", json=bad, headers=auth_headers).status_code == 422


def test_clip_quelle_ausserhalb_des_projekts_wird_abgelehnt(client, auth_headers):
    sid = client.post(f"{P}/songs", json={"title": "a"}, headers=auth_headers).json()["id"]
    body = {"title": "a", "expected_version": 1,
            "tracks": [{"id": "t", "clips": [{"id": "c", "source_rel": "../../../etc/passwd", "src_end": 1}]}]}
    r = client.put(f"{P}/songs/{sid}", json=body, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "source_outside_project"


def test_papierkorb_und_wiederherstellen(client, auth_headers):
    sid = client.post(f"{P}/songs", json={"title": "weg"}, headers=auth_headers).json()["id"]
    assert client.delete(f"{P}/songs/{sid}", headers=auth_headers).status_code == 200
    assert client.get(f"{P}/songs/{sid}", headers=auth_headers).status_code == 404
    assert [s["id"] for s in client.get(f"{P}/trash", headers=auth_headers).json()] == [sid]
    assert client.post(f"{P}/trash/{sid}/restore", headers=auth_headers).status_code == 200
    assert client.get(f"{P}/songs/{sid}", headers=auth_headers).status_code == 200
    assert client.post(f"{P}/trash/{sid}/restore", headers=auth_headers).status_code == 404
    assert client.post(f"{P}/trash/gibtsnicht/restore", headers=auth_headers).status_code == 404
    assert client.delete(f"{P}/songs/gibtsnicht", headers=auth_headers).status_code == 404


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg fehlt")
def test_upload_und_bibliothek_und_loeschen(client, auth_headers, tmp_path):
    audio = _tone(tmp_path)
    r = client.post(f"{P}/library/upload", files={"file": ("demo.mp3", audio, "audio/mpeg")}, headers=auth_headers)
    assert r.status_code == 200, r.text
    rel = r.json()["source_rel"]
    lib = client.get(f"{P}/library", headers=auth_headers).json()
    assert [i["source_rel"] for i in lib] == [rel]
    r = client.post(f"{P}/library/upload", files={"file": ("x.mp3", b"nope", "audio/mpeg")}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "upload_rejected"
    assert client.post(f"{P}/library/delete", json={"source_rel": rel}, headers=auth_headers).status_code == 200
    assert client.post(f"{P}/library/delete", json={"source_rel": rel}, headers=auth_headers).status_code == 404


def test_datei_ausliefern_nur_audio_im_projekt(client, auth_headers, other_headers, tmp_path, ws):
    if shutil.which("ffmpeg"):
        (ws / "generated").mkdir(exist_ok=True)
        (ws / "generated" / "a.mp3").write_bytes(_tone(tmp_path))
        r = client.get(f"{P}/file", params={"rel": "generated/a.mp3"}, headers=auth_headers)
        assert r.status_code == 200 and r.headers["content-type"].startswith("audio/")
        token = auth_headers["Authorization"].split(" ", 1)[1]
        r = client.get(f"{P}/file", params={"rel": "generated/a.mp3", "token": token})
        assert r.status_code == 200, "Player (<audio>) muss mit ?token= laden können"
        assert client.get(f"{P}/file", params={"rel": "generated/a.mp3"}).status_code == 401
        fremd = other_headers["Authorization"].split(" ", 1)[1]
        r = client.get(f"{P}/file", params={"rel": "generated/a.mp3", "token": fremd})
        assert r.status_code == 404, "Nicht-Mitglied darf über ?token= keine Projektdatei laden"
    (ws / "geheim.txt").write_text("x")
    assert client.get(f"{P}/file", params={"rel": "geheim.txt"}, headers=auth_headers).status_code == 404
    assert client.get(f"{P}/file", params={"rel": "../../config/users.json"}, headers=auth_headers).status_code == 404


def test_modelle_liste(client, auth_headers, monkeypatch):
    from backend.providers import openrouter

    async def live():
        return [{"id": "google/lyria-3-pro-preview", "name": "Lyria 3 Pro"}]
    monkeypatch.setattr(openrouter, "_live_audio_models", live)
    r = client.get(f"{MOD_PREFIX}/models", headers=auth_headers)
    assert r.status_code == 200
    m = r.json()[0]
    assert m["id"] == "google/lyria-3-pro-preview" and m["lyrics"] is True and m["audio_ref"] is False


def test_erzeugen_fehler_wird_als_422_gemeldet(client, auth_headers, monkeypatch):
    from backend import generate, providers

    async def boom(*a, **k):
        raise providers.ProviderError("Kein OpenRouter-Schlüssel eingerichtet")
    monkeypatch.setattr(generate, "generate_clip", boom)
    r = client.post(f"{P}/generate", json={"model": "google/lyria-3-pro-preview", "request": {"description": "x"}},
                    headers=auth_headers)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "generation_failed"
    assert "Schlüssel" in r.json()["detail"]["params"]["message"]


def test_erzeugen_leerer_auftrag_422(client, auth_headers):
    r = client.post(f"{P}/generate", json={"model": "google/lyria-3-pro-preview", "request": {}}, headers=auth_headers)
    assert r.status_code == 422


def test_umbenennen_route(client, auth_headers, other_headers, ws):
    (ws / "generated").mkdir(exist_ok=True)
    (ws / "generated" / "a.mp3").write_bytes(b"ID3")
    body = {"source_rel": "generated/a.mp3", "name": "Mein Lied"}
    assert client.post(f"{P}/library/label", json=body, headers=other_headers).status_code == 404
    assert client.post(f"{P}/library/label", json=body, headers=auth_headers).status_code == 200
    r = client.post(f"{P}/library/label", json={"source_rel": "geheim.mp3", "name": "x"}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "label_rejected"
