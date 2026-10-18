"""Studio 5c-1: Sprechtext je Shot und „Sprache erzeugen“ (studio/SPEC.md „Bauplan 5c“). Anbieter ersetzt, kein Netz."""
from __future__ import annotations

import json

from _timeline_helpers import _code
from _voice_helpers import P, FakeVoice, scene_with_shot, voice, wait_job  # noqa: F401 – Fixture

from conftest import MOD_PREFIX, PROJECT_ID


def test_shot_has_speech_text_and_voice(client, auth_headers, ws, voice) -> None:
    sc, s = scene_with_shot(client, auth_headers, speech="Da ist er!", voice="af_bella")
    assert s["speech"] == "Da ist er!" and s["voice"] == "af_bella" and s["voice_rel"] is None
    long = client.put(f"{P}/scenes/{sc['id']}/shots/{s['id']}", headers=auth_headers, json={"speech": "x" * 1500}).json()
    assert len(long["speech"]) == 1000
    old = json.loads((ws / f"studio/scenes/{sc['id']}.json").read_text())
    del old["shots"][0]["speech"], old["shots"][0]["voice"], old["shots"][0]["voice_rel"]
    (ws / f"studio/scenes/{sc['id']}.json").write_text(json.dumps(old))            # alte Szene ohne die Felder
    got = client.get(f"{P}", headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert got["speech"] == "" and got["voice"] == "" and got["voice_rel"] is None


def test_make_speech(client, auth_headers, ws, voice) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"voice": "test/tts"}})
    sc, s = scene_with_shot(client, auth_headers, speech="Da ist er!", voice="af_nicole")
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=auth_headers)
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "speech"
    job = wait_job(client, auth_headers, s["id"])
    assert job["status"] == "done", job
    assert voice.calls == [{"text": "Da ist er!", "voice": "af_nicole", "model": "test/tts"}]
    rel = job["result"]["voice_rel"]
    assert rel.startswith("studio/media/voice/") and rel.endswith(".wav") and (ws / rel).is_file()
    meta = json.loads((ws / f"{rel}.json").read_text())
    assert meta["text"] == "Da ist er!" and meta["voice"] == "af_nicole" and meta["model"] == "test/tts"
    assert meta["shot_id"] == s["id"] and abs(meta["duration"] - 1.5) < 0.1
    shot = client.get(f"{P}", headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert shot["voice_rel"] == rel
    lib = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]
    mine = [i for i in lib if i["rel"] == rel]
    assert mine and mine[0]["kind"] == "audio" and mine[0]["source"] == "studio_voice" and abs(mine[0]["duration"] - 1.5) < 0.1


def test_server_default_model_and_voice(client, auth_headers, ws, voice) -> None:
    sc, s = scene_with_shot(client, auth_headers, speech="Hallo")
    client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=auth_headers)
    assert wait_job(client, auth_headers, s["id"])["status"] == "done"
    assert voice.calls[0]["model"] == "server/tts" and voice.calls[0]["voice"] == ""


def test_speech_needs_text(client, auth_headers, ws, voice) -> None:
    sc, s = scene_with_shot(client, auth_headers)
    assert _code(client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=auth_headers)) == "400 studio_speech_needs_text"
    assert _code(client.post(f"{P}/scenes/{sc['id']}/shots/{'f' * 32}/speech", headers=auth_headers)) == "404 studio_not_found"
    assert voice.calls == []


def test_provider_errors_and_bad_audio(client, auth_headers, ws, monkeypatch) -> None:
    from _voice_helpers import FakeVoice as FV
    monkeypatch.setattr("backend.voice_provider.server_default_model", lambda: "server/tts")
    for fake, code in ((FV(error="no_key"), "no_key"), (FV(error="provider_rejected"), "provider_rejected"), (FV(data=b"<html>kaputt"), "bad_audio")):
        monkeypatch.setattr("backend.voice_provider.synthesize", fake)
        sc, s = scene_with_shot(client, auth_headers, speech="Hallo")
        client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=auth_headers)
        job = wait_job(client, auth_headers, s["id"])
        assert (job["status"], job["error"]) == ("failed", code)
        assert client.get(f"{P}", headers=auth_headers).json()["scenes"][-1]["shots"][0]["voice_rel"] is None
    assert not list((ws / "studio/media/voice").glob("*")) if (ws / "studio/media/voice").exists() else True


def test_new_speech_replaces_and_keeps_old_file(client, auth_headers, ws, voice) -> None:
    sc, s = scene_with_shot(client, auth_headers, speech="Eins")
    client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=auth_headers)
    first = wait_job(client, auth_headers, s["id"])["result"]["voice_rel"]
    client.put(f"{P}/scenes/{sc['id']}/shots/{s['id']}", headers=auth_headers, json={"speech": "Zwei"})
    client.post(f"{P}/scenes/{sc['id']}/shots/{s['id']}/speech", headers=auth_headers)
    import time
    time.sleep(0.3)
    second = wait_job(client, auth_headers, s["id"])["result"]["voice_rel"]
    assert second != first and (ws / first).is_file()                          # alte Fassung bleibt in der Bibliothek
    assert client.get(f"{P}", headers=auth_headers).json()["scenes"][0]["shots"][0]["voice_rel"] == second


def test_voices_route(client, auth_headers, other_headers, voice) -> None:
    r = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/voices", headers=auth_headers, params={"model": "x/y"})
    assert r.status_code == 200 and r.json() == {"model": "x/y", "voices": ["af_bella", "af_nicole"]}
    assert client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/voices", headers=auth_headers).json()["model"] == "server/tts"
    assert client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/voices", headers=other_headers).status_code == 404


def test_batch_speech_for_all_shots_with_text(client, auth_headers, ws, voice) -> None:
    sc, a = scene_with_shot(client, auth_headers, speech="Eins")
    b = client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "x", "speech": "Zwei"}).json()
    client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "ohne Text"})
    assert client.get(f"{P}/batch/speech_all", headers=auth_headers).json()["count"] == 2
    r = client.post(f"{P}/batch/speech_all", headers=auth_headers)
    assert r.status_code == 202, r.text
    job = wait_job(client, auth_headers, f"batch:{PROJECT_ID}")
    assert job["status"] == "done" and job["result"] == {"done": 2, "failed": 0}
    assert sorted(c["text"] for c in voice.calls) == ["Eins", "Zwei"]
    shots = client.get(f"{P}", headers=auth_headers).json()["scenes"][0]["shots"]
    assert [bool(x["voice_rel"]) for x in shots] == [True, True, False]
    assert client.get(f"{P}/batch/speech_all", headers=auth_headers).json()["count"] == 0          # schon fertig → nichts mehr
    _ = a, b
