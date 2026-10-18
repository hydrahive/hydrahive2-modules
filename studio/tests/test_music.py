"""Studio 5c-2: Musik erzeugen (studio/SPEC.md „Nachtrag 5c-2“). Anbieter ersetzt, kein Netz."""
from __future__ import annotations

import json

from _timeline_helpers import _code
from _voice_helpers import P, wait_job
from conftest import MOD_PREFIX, PROJECT_ID

pytest_plugins = ["_music_helpers"]                # Fixture `music`

M = f"{MOD_PREFIX}/projects/{PROJECT_ID}/music"
TARGET = f"music:{PROJECT_ID}"


def test_music_for_the_film(client, auth_headers, ws, music) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"music": "test/lyria"}})
    r = client.post(M, headers=auth_headers, json={"description": "ruhige Streicher, Nordsee", "seconds": 40})
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "music"
    job = wait_job(client, auth_headers, TARGET)
    assert job["status"] == "done", job
    call = music.calls[0]
    assert call["model"] == "test/lyria"
    assert call["prompt"].startswith("ruhige Streicher, Nordsee") and "Instrumental" in call["prompt"] and "40 seconds" in call["prompt"]
    res = job["result"]
    rel = res["rel"]
    assert rel.startswith("studio/media/music/") and (ws / rel).is_file()
    assert res["scene_id"] == "" and res["seconds"] == 40 and abs(res["duration"] - 3.0) < 0.1
    meta = json.loads((ws / f"{rel}.json").read_text())
    assert meta["description"] == "ruhige Streicher, Nordsee" and meta["prompt"] == call["prompt"] and meta["model"] == "test/lyria"
    assert meta["seconds"] == 40 and abs(meta["duration"] - 3.0) < 0.1
    lib = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]
    mine = [i for i in lib if i["rel"] == rel]
    assert mine and mine[0]["kind"] == "music" and mine[0]["source"] == "studio_music" and mine[0]["duration"] > 2
    assert not (ws / "studio/timelines/main.json").exists()             # Zeitleiste fasst der Auftrag nicht an


def test_music_for_a_scene_and_default_model(client, auth_headers, ws, music) -> None:
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Sturm"}).json()
    client.post(M, headers=auth_headers, json={"description": "Gewitter", "seconds": 12, "scene_id": sc["id"]})
    job = wait_job(client, auth_headers, TARGET)
    assert job["status"] == "done" and job["result"]["scene_id"] == sc["id"]
    assert music.calls[0]["model"] == "server/lyria"
    assert _code(client.post(M, headers=auth_headers, json={"description": "x", "seconds": 10, "scene_id": "f" * 32})) == "404 studio_not_found"


def test_rules(client, auth_headers, ws, music) -> None:
    assert _code(client.post(M, headers=auth_headers, json={"description": "  ", "seconds": 10})) == "400 studio_music_needs_text"
    for bad in (4, 181, "30", True, None):
        assert _code(client.post(M, headers=auth_headers, json={"description": "x", "seconds": bad})) == "400 studio_music_invalid", bad
    long = client.post(M, headers=auth_headers, json={"description": "y" * 3000, "seconds": 30})
    assert long.status_code == 202
    wait_job(client, auth_headers, TARGET)
    assert len(music.calls[0]["prompt"].split(".")[0]) <= 2000
    assert music.calls == music.calls[:1]                                  # ungültige Anfragen haben nichts gesendet


def test_only_one_music_job_at_a_time(client, auth_headers, ws, monkeypatch) -> None:
    import time

    from _music_helpers import FakeMusic

    class Slow(FakeMusic):
        def __call__(self, prompt, model):
            time.sleep(0.4)
            return super().__call__(prompt, model)

    monkeypatch.setattr("backend.music_provider.generate", Slow())
    monkeypatch.setattr("backend.music_provider.server_default_model", lambda: "m")
    assert client.post(M, headers=auth_headers, json={"description": "a", "seconds": 10}).status_code == 202
    assert _code(client.post(M, headers=auth_headers, json={"description": "b", "seconds": 10})) == "409 studio_music_running"
    assert wait_job(client, auth_headers, TARGET)["status"] == "done"


def test_provider_errors_and_bad_audio(client, auth_headers, ws, monkeypatch) -> None:
    from _music_helpers import FakeMusic
    monkeypatch.setattr("backend.music_provider.server_default_model", lambda: "m")
    for fake, code in ((FakeMusic(error="no_key"), "no_key"), (FakeMusic(error="empty_answer"), "empty_answer"),
                       (FakeMusic(data=b"<html>kaputt"), "bad_audio")):
        monkeypatch.setattr("backend.music_provider.generate", fake)
        client.post(M, headers=auth_headers, json={"description": "x", "seconds": 10})
        job = wait_job(client, auth_headers, TARGET)
        assert (job["status"], job["error"]) == ("failed", code)
    d = ws / "studio/media/music"
    assert not d.exists() or not [p for p in d.iterdir() if p.suffix != ".json"]


def test_only_members(client, other_headers, music) -> None:
    assert client.post(M, headers=other_headers, json={"description": "x", "seconds": 10}).status_code == 404
    assert client.get(f"{M}/defaults", headers=other_headers).status_code == 404


def test_defaults_from_screenplay_and_scene(client, auth_headers, ws, music) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"logline": "Ein alter Fischer kehrt heim.", "look": {"style": "nebliges Licht, Nordsee"}})
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Sturm", "description": "Gewitter über dem Hafen"}).json()
    client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "x", "duration": 7})
    client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "y", "duration": 5})
    d = client.get(f"{M}/defaults", headers=auth_headers).json()
    assert d["film"]["description"].startswith("Ein alter Fischer kehrt heim.") and "nebliges Licht" in d["film"]["description"]
    assert d["film"]["seconds"] == 12 and d["model"] == "server/lyria"
    assert d["scenes"] == [{"id": sc["id"], "title": "Sturm", "description": "Gewitter über dem Hafen", "seconds": 12}]
    empty = client.get(f"{M}/defaults", headers=auth_headers)
    assert empty.status_code == 200
