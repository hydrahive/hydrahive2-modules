"""Studio 3b: Video für einen Shot (studio/SPEC.md „Bauplan Etappe 3“). Der Anbieter wird ersetzt."""
from __future__ import annotations

import json
import time

import pytest
from _gen_helpers import PNG, P, _shot, _wait
from _video_helpers import MP4, FakeVideo, _install
from conftest import MOD_PREFIX, PROJECT_ID

pytest_plugins = ["_gen_helpers", "_video_helpers"]
def _with_image(client, h, ws) -> tuple[dict, dict]:
    _, sc, shot = _shot(client, h, ws, with_ref=False)
    (ws / "bilder").mkdir(exist_ok=True)
    (ws / "bilder/start.png").write_bytes(PNG)
    from backend import shots as shots_mod
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    scene["shots"][0].update({"image_rel": "bilder/start.png", "status": "image_ready", "duration": 7})
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
    client.put(f"{P}/screenplay", headers=h, json={"models": {"video": "test/video-billig"}, "aspect_ratio": "16:9"})
    return sc, shot


def test_video_from_image(client, auth_headers, ws, video) -> None:
    sc, shot = _with_image(client, auth_headers, ws)
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/video", headers=auth_headers, json={})
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "video"
    job = _wait(client, auth_headers, sc["id"], shot["id"])
    assert job["status"] == "done", job

    sub = dict(video.calls)["submit"]
    assert sub["model"] == "test/video-billig" and sub["duration"] == 7 and sub["aspect_ratio"] == "16:9"
    assert sub["image_url"].startswith("data:image/png;base64,")             # Startbild = gewähltes Bild
    assert "boat enters harbour" in sub["prompt"] and "wide establishing shot" in sub["prompt"]   # Shot + Kamera
    saved = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert saved["status"] == "done" and saved["image_rel"] == "bilder/start.png"
    assert saved["video_rel"].startswith("studio/media/videos/") and saved["video_rel"].endswith(".mp4")
    assert (ws / saved["video_rel"]).read_bytes() == MP4
    meta = json.loads((ws / (saved["video_rel"] + ".json")).read_text())
    assert meta["model"] == "test/video-billig" and meta["source_image"] == "bilder/start.png" and meta["duration"] == 7
    lib = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]
    mine = [i for i in lib if i["rel"] == saved["video_rel"]]
    assert mine and mine[0]["kind"] == "video" and mine[0]["source"] == "studio"


def test_duration_snaps_to_allowed_values(client, auth_headers, ws, monkeypatch) -> None:
    fake = FakeVideo(durations=[4, 6, 8])
    _install(monkeypatch, fake)
    sc, shot = _with_image(client, auth_headers, ws)                          # Shot-Dauer 7 → nächste erlaubte
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/video", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    assert dict(fake.calls)["submit"]["duration"] in (6, 8)
    assert dict(fake.calls)["wait"]["duration"] == dict(fake.calls)["submit"]["duration"]


def test_needs_an_image(client, auth_headers, ws, video) -> None:
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/video", headers=auth_headers, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_video_needs_image"
    assert video.calls == []


@pytest.mark.parametrize("step,code", [("submit", "no_key"), ("wait", "video_failed"), ("wait", "timeout"), ("download", "too_big")])
def test_failure_keeps_image_and_marks_shot(client, auth_headers, ws, monkeypatch, step, code) -> None:
    _install(monkeypatch, FakeVideo(fail_at=step, code=code))
    sc, shot = _with_image(client, auth_headers, ws)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/video", headers=auth_headers, json={})
    job = _wait(client, auth_headers, sc["id"], shot["id"])
    assert job["status"] == "failed" and job["error"] == code
    s = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert s["status"] == "failed" and s["video_rel"] is None and s["image_rel"] == "bilder/start.png"
    assert not list((ws / "studio").glob("media/videos/*"))                    # keine halben Dateien


def test_shot_shows_video_processing_while_running(client, auth_headers, ws, monkeypatch) -> None:
    _install(monkeypatch, FakeVideo(delay=0.6))
    sc, shot = _with_image(client, auth_headers, ws)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/video", headers=auth_headers, json={})
    time.sleep(0.25)
    assert client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]["status"] == "video_processing"
    _wait(client, auth_headers, sc["id"], shot["id"])


def test_at_most_two_videos_at_once(client, auth_headers, ws, monkeypatch) -> None:
    fake = FakeVideo(delay=0.5)
    _install(monkeypatch, fake)
    sc, first = _with_image(client, auth_headers, ws)
    from backend import shots as shots_mod
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    extra = [{**scene["shots"][0], "id": f"{i}" * 32} for i in range(1, 4)]
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"] + extra)
    ids = [first["id"]] + [e["id"] for e in extra]
    for sid in ids:
        assert client.post(f"{P}/scenes/{sc['id']}/shots/{sid}/video", headers=auth_headers, json={}).status_code == 202
    for sid in ids:
        assert _wait(client, auth_headers, sc["id"], sid, timeout=10)["status"] == "done"
    assert fake.peak == 2


def test_interrupted_video_marks_shot_failed(client, auth_headers, ws) -> None:
    from backend import jobs
    from backend import shots as shots_mod
    sc, shot = _with_image(client, auth_headers, ws)
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    scene["shots"][0]["status"] = "video_processing"
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
    (ws / "studio/jobs").mkdir(parents=True, exist_ok=True)
    (ws / "studio/jobs" / f"{'9' * 32}.json").write_text(json.dumps(
        {"id": "9" * 32, "kind": "video", "target": shot["id"], "scene_id": sc["id"], "status": "running", "created_at": "2026-10-17T10:00:00Z"}))
    jobs.recover(PROJECT_ID)
    s = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert s["status"] == "failed"                                             # nicht ewig „Video läuft“


def test_plan_read_repairs_interrupted_video(client, auth_headers, ws) -> None:
    """Auch ohne Blick in die Aufträge: Beim Laden des Plans wird ein liegengebliebenes Video als fehlgeschlagen gezeigt."""
    from backend import shots as shots_mod
    sc, shot = _with_image(client, auth_headers, ws)
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    scene["shots"][0]["status"] = "video_processing"
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
    (ws / "studio/jobs").mkdir(parents=True, exist_ok=True)
    (ws / "studio/jobs" / f"{'8' * 32}.json").write_text(json.dumps(
        {"id": "8" * 32, "kind": "video", "target": shot["id"], "scene_id": sc["id"], "status": "running", "created_at": "2026-10-17T10:00:00Z"}))
    assert client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]["status"] == "failed"


def test_start_image_must_be_a_real_image_in_the_project(client, auth_headers, ws, video) -> None:
    """Zeigt das Bild des Shots nach draußen (Verknüpfung) oder fehlt es, geht nichts an den Anbieter."""
    import os
    sc, shot = _with_image(client, auth_headers, ws)
    outside = ws.parent / "fremd.png"
    outside.write_bytes(PNG)
    (ws / "bilder/start.png").unlink()
    os.symlink(outside, ws / "bilder/start.png")
    try:
        client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/video", headers=auth_headers, json={})
        job = _wait(client, auth_headers, sc["id"], shot["id"])
        assert job["status"] == "failed" and job["error"] == "image_gone"
        assert [c for c, _ in video.calls if c == "submit"] == []
        assert client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]["status"] == "failed"
    finally:
        (ws / "bilder/start.png").unlink()
        outside.unlink()
