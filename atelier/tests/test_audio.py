"""Atelier — Audio: Studio-Sound-Anker, Sound-Profile, Bibliothek, Generierung (gemockt)."""
from __future__ import annotations

from backend import music
from conftest import OTHER_PROJECT_ID, PROJECT_ID

PREFIX = f"/api/modules/atelier/projects/{PROJECT_ID}"
OTHER_PREFIX = f"/api/modules/atelier/projects/{OTHER_PROJECT_ID}"


# ---------------------------------------------------------------- Auth + Projekt-Guard
def test_braucht_auth(client):
    assert client.get(f"{PREFIX}/audio/profiles").status_code == 401


def test_fremdes_projekt_404(client, auth_headers):
    # testuser ist nicht Mitglied von OTHER_PROJECT_ID
    assert client.get(f"{OTHER_PREFIX}/audio/profiles", headers=auth_headers).status_code == 404


def test_unbekanntes_projekt_404(client, auth_headers):
    r = client.get("/api/modules/atelier/projects/does-not-exist/audio/profiles", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------- Studio-Sound-Anker
def test_anchor_get_set(client, auth_headers):
    assert client.get(f"{PREFIX}/audio/anchor", headers=auth_headers).json() == {"music_style_anchor": ""}
    r = client.put(f"{PREFIX}/audio/anchor", json={"music_style_anchor": "synthwave, 80s retro, driving bassline"}, headers=auth_headers)
    assert r.json()["music_style_anchor"] == "synthwave, 80s retro, driving bassline"
    assert client.get(f"{PREFIX}/audio/anchor", headers=auth_headers).json()["music_style_anchor"] == "synthwave, 80s retro, driving bassline"


# ---------------------------------------------------------------- Sound-Profile CRUD
def test_profile_crud(client, auth_headers):
    assert client.get(f"{PREFIX}/audio/profiles", headers=auth_headers).json() == []
    r = client.post(f"{PREFIX}/audio/profiles", json={"name": "Hauptthema", "description": "warm strings, 90 BPM"}, headers=auth_headers)
    assert r.status_code == 200
    pid = r.json()["id"]
    items = client.get(f"{PREFIX}/audio/profiles", headers=auth_headers).json()
    assert len(items) == 1 and items[0]["name"] == "Hauptthema"

    r = client.put(f"{PREFIX}/audio/profiles/{pid}", json={"name": "Hauptthema v2", "description": "warm strings, 90 BPM"}, headers=auth_headers)
    assert r.json()["name"] == "Hauptthema v2"

    assert client.delete(f"{PREFIX}/audio/profiles/{pid}", headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/audio/profiles", headers=auth_headers).json() == []


def test_profile_update_unknown_404(client, auth_headers):
    r = client.put(f"{PREFIX}/audio/profiles/{'a' * 32}", json={"name": "x"}, headers=auth_headers)
    assert r.status_code == 404


def test_profile_delete_unknown_404(client, auth_headers):
    assert client.delete(f"{PREFIX}/audio/profiles/{'a' * 32}", headers=auth_headers).status_code == 404


def test_profile_per_projekt_isoliert(client, auth_headers, other_headers):
    client.post(f"{PREFIX}/audio/profiles", json={"name": "Mine"}, headers=auth_headers)
    # 'other' Projekt sieht die Profile von PROJECT_ID nicht (anderes Projekt)
    assert client.get(f"{OTHER_PREFIX}/audio/profiles", headers=other_headers).json() == []


# ---------------------------------------------------------------- Bibliothek + Generierung (gemockt)
def test_generate_und_library(client, auth_headers, monkeypatch):
    async def fake_generate_music(*, model, prompt):
        assert "driving synth" in prompt
        return b"FAKE_MP3_BYTES"
    monkeypatch.setattr(music, "generate_music", fake_generate_music)

    client.put(f"{PREFIX}/audio/anchor", json={"music_style_anchor": "driving synth, retro"}, headers=auth_headers)
    r = client.post(f"{PREFIX}/audio/generate", json={"scene": "chase scene"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["rel"].startswith("audio/") and data["rel"].endswith(".mp3")
    assert "driving synth" in data["prompt"] and "chase scene" in data["prompt"]

    lib = client.get(f"{PREFIX}/audio/library", headers=auth_headers).json()
    assert len(lib) == 1 and lib[0]["rel"] == data["rel"]


def test_generate_mit_profilen(client, auth_headers, monkeypatch):
    captured = {}
    async def fake_generate_music(*, model, prompt):
        captured["prompt"] = prompt
        return b"FAKE"
    monkeypatch.setattr(music, "generate_music", fake_generate_music)

    pid = client.post(f"{PREFIX}/audio/profiles", json={"name": "Held", "description": "heroic brass"}, headers=auth_headers).json()["id"]
    client.post(f"{PREFIX}/audio/generate", json={"scene": "finale", "profile_ids": [pid]}, headers=auth_headers)
    assert "heroic brass" in captured["prompt"]


def test_generate_leerer_prompt_422(client, auth_headers):
    # kein Anchor, kein Profil, keine Szene → leerer Prompt
    r = client.post(f"{PREFIX}/audio/generate", json={}, headers=auth_headers)
    assert r.status_code == 422


def test_generate_music_error_422(client, auth_headers, monkeypatch):
    async def fake_fail(*, model, prompt):
        raise music.MusicError("Kein OpenRouter-API-Key konfiguriert.")
    monkeypatch.setattr(music, "generate_music", fake_fail)
    r = client.post(f"{PREFIX}/audio/generate", json={"scene": "test"}, headers=auth_headers)
    assert r.status_code == 422


def test_delete_track(client, auth_headers, monkeypatch):
    async def fake_generate_music(*, model, prompt):
        return b"FAKE"
    monkeypatch.setattr(music, "generate_music", fake_generate_music)
    rel = client.post(f"{PREFIX}/audio/generate", json={"scene": "x"}, headers=auth_headers).json()["rel"]

    assert client.post(f"{PREFIX}/audio/library/delete", json={"rel": rel}, headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/audio/library", headers=auth_headers).json() == []


def test_delete_track_unknown_404(client, auth_headers):
    r = client.post(f"{PREFIX}/audio/library/delete", json={"rel": "audio/does-not-exist.mp3"}, headers=auth_headers)
    assert r.status_code == 404


def test_delete_track_path_traversal_404(client, auth_headers):
    r = client.post(f"{PREFIX}/audio/library/delete", json={"rel": "../../../etc/passwd"}, headers=auth_headers)
    assert r.status_code == 404
