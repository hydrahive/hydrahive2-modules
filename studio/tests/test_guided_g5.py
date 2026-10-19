"""Studio G5: „Film machen“ als ein Auftrag (studio/SPEC.md „Bauplan G5“). Stimme/Musik ersetzt, ffmpeg echt (klein)."""
from __future__ import annotations

import json
import time

from _render_helpers import R, make_image, needs_ffmpeg, probe
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

pytest_plugins = ["_voice_helpers", "_music_helpers"]
P = f"{R}/plan"


def _film(client, h, ws, n: int = 2, *, speech: str = "") -> list[tuple[str, str]]:
    client.put(f"{P}/screenplay", headers=h, json={"title": "Hydras Jahr", "logline": "Ein Wesen erlebt ein Jahr.", "aspect_ratio": "16:9",
                                                    "language": "de"})
    out = []
    for i in range(n):
        img = make_image(ws, f"b{i}.png", "320x180")
        sc = client.post(f"{P}/scenes", headers=h, json={"title": f"S{i}", "description": f"Hydra tut Ding {i}."}).json()
        sh = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": f"p{i}", "duration": 2, "speech": speech if i == 0 else ""}).json()
        from backend import shots as shots_mod
        scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
        scene["shots"][0].update({"image_rel": img, "status": "image_ready", "still": True})
        shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
        out.append((sc["id"], sh["id"]))
    return out


def _wait_film(client, h, timeout: float = 60.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["kind"] == "film"]
        if jobs and jobs[0]["status"] in ("done", "failed", "cancelled"):
            return jobs[0]
        time.sleep(0.1)
    raise AssertionError("Film nicht fertig")


@needs_ffmpeg
def test_film_plain(client, auth_headers, ws, voice, music) -> None:
    _film(client, auth_headers, ws)
    r = client.post(f"{R}/film", headers=auth_headers, json={"music": False, "voice": False, "subtitles": False})
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "film" and r.json()["progress"]["total"] == 5
    job = _wait_film(client, auth_headers)
    assert job["status"] == "done", job
    res = job["result"]
    assert res["rel"].startswith("studio/renders/") and (ws / res["rel"]).is_file()
    assert res["music"] is False and res["subtitles"] is False and res["voice_failed"] == 0
    assert abs(float(probe(ws / res["rel"])["format"]["duration"]) - 4.0) < 0.5           # 2 Standbilder à 2 s
    assert voice.calls == [] and music.calls == []
    tl = client.get(f"{R}/timeline", headers=auth_headers).json()
    assert len([c for t in tl["tracks"] if t["id"] == "V1" for c in t["clips"]]) == 2
    assert json.loads((ws / "studio/film.json").read_text())["revision"] == tl["revision"]
    assert client.get(f"{R}/renders", headers=auth_headers).json()["renders"][0]["rel"] == res["rel"]


@needs_ffmpeg
def test_film_with_everything(client, auth_headers, ws, voice, music) -> None:
    _film(client, auth_headers, ws, speech="Eigener Text.")
    client.post(f"{R}/film", headers=auth_headers, json={"music": True, "voice": True, "subtitles": True})
    job = _wait_film(client, auth_headers)
    assert job["status"] == "done", job
    res = job["result"]
    # Stimme: Shot 0 behält seinen eigenen Text, Shot 1 bekommt den Kartentext
    assert sorted(call["text"] for call in voice.calls) == ["Eigener Text.", "Hydra tut Ding 1."]
    plan = client.get(P, headers=auth_headers).json()
    assert [s["shots"][0]["speech"] for s in plan["scenes"]] == ["Eigener Text.", "Hydra tut Ding 1."]
    # Musik: eine, Beschreibung aus Titel/Logline, Länge = Film (5–180 → mindestens 5)
    assert len(music.calls) == 1 and "Hydras Jahr" in music.calls[0]["prompt"] and "Ein Wesen erlebt ein Jahr" in music.calls[0]["prompt"]
    tl = client.get(f"{R}/timeline", headers=auth_headers).json()
    a2 = next(t for t in tl["tracks"] if t["id"] == "A2")["clips"]
    assert len(a2) == 1 and a2[0]["start"] == 0
    a1 = next(t for t in tl["tracks"] if t["id"] == "A1")["clips"]
    assert len(a1) == 2
    assert res["music"] is True and res["subtitles"] is True
    streams = [s["codec_type"] for s in probe(ws / res["rel"])["streams"]]
    assert "audio" in streams and "subtitle" in streams


@needs_ffmpeg
def test_existing_music_stays(client, auth_headers, ws, voice, music) -> None:
    _film(client, auth_headers, ws)
    client.post(f"{R}/film", headers=auth_headers, json={"music": True, "voice": False, "subtitles": False})
    _wait_film(client, auth_headers)
    client.post(f"{R}/film", headers=auth_headers, json={"music": True, "voice": False, "subtitles": False})
    job = _wait_film(client, auth_headers)
    assert job["status"] == "done" and len(music.calls) == 1                         # zweites Mal keine neue Musik


@needs_ffmpeg
def test_failures_do_not_stop_the_film(client, auth_headers, ws, monkeypatch) -> None:
    from _music_helpers import FakeMusic
    from _voice_helpers import FakeVoice
    monkeypatch.setattr("backend.voice_provider.synthesize", FakeVoice(error="no_key"))
    monkeypatch.setattr("backend.voice_provider.server_default_model", lambda: "server/tts")
    monkeypatch.setattr("backend.music_provider.generate", FakeMusic(error="no_key"))
    monkeypatch.setattr("backend.music_provider.server_default_model", lambda: "server/lyria")
    _film(client, auth_headers, ws)
    client.post(f"{R}/film", headers=auth_headers, json={"music": True, "voice": True, "subtitles": True})
    job = _wait_film(client, auth_headers)
    assert job["status"] == "done", job
    res = job["result"]
    assert res["voice_failed"] == 2 and res["music"] is False
    assert "music_failed" in res["notes"]


@needs_ffmpeg
def test_no_speech_means_no_subtitles(client, auth_headers, ws, voice, music) -> None:
    _film(client, auth_headers, ws)
    client.post(f"{R}/film", headers=auth_headers, json={"music": False, "voice": False, "subtitles": True})
    job = _wait_film(client, auth_headers)
    assert job["status"] == "done" and job["result"]["subtitles"] is False
    assert "no_speech" in job["result"]["notes"]


@needs_ffmpeg
def test_hand_edited_timeline_asks(client, auth_headers, ws, voice, music) -> None:
    _film(client, auth_headers, ws)
    client.post(f"{R}/film", headers=auth_headers, json={})
    _wait_film(client, auth_headers)
    tl = client.get(f"{R}/timeline", headers=auth_headers).json()
    v1 = next(t for t in tl["tracks"] if t["id"] == "V1")["clips"]
    client.put(f"{R}/timeline", headers=auth_headers, json={"revision": tl["revision"], "fps": tl["fps"],
                                                             "tracks": [{"id": "V1", "kind": "video", "clips": v1[:1]}]})
    r = client.post(f"{R}/film", headers=auth_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_film_edited"
    client.post(f"{R}/film", headers=auth_headers, json={"rebuild": False})
    job = _wait_film(client, auth_headers)
    assert abs(job["result"]["duration"] - 2.0) < 0.5                                 # so gelassen: nur ein Clip
    client.post(f"{R}/film", headers=auth_headers, json={"rebuild": True})
    job = _wait_film(client, auth_headers)
    assert abs(job["result"]["duration"] - 4.0) < 0.5                                 # neu zusammengesetzt


def test_bad_options_and_empty(client, auth_headers, ws) -> None:
    for body in ({"music": "ja"}, {"voice": 1}, {"subtitles": None}, {"rebuild": "x"}):
        r = client.post(f"{R}/film", headers=auth_headers, json=body)
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_film_invalid", body
    r = client.post(f"{R}/film", headers=auth_headers, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_timeline_no_shots"


def test_foreign_project(client, auth_headers) -> None:
    assert client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/film", headers=auth_headers, json={}).status_code == 404
