"""Studio 3c: Sammelaufträge – alle Szenen zerlegen, Bilder für alle, Videos für alle (studio/SPEC.md „Bauplan 3c“)."""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

from _gen_helpers import PNG, FakeProvider, P
from _video_helpers import FakeVideo, _install
from conftest import PROJECT_ID

pytest_plugins = ["_gen_helpers", "_video_helpers"]
LLM = "backend.director.llm_client.complete"


def _wait_batch(client, h, job_id: str, timeout: float = 10.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        j = {x["id"]: x for x in client.get(f"{P}/jobs", headers=h).json()["jobs"]}.get(job_id)
        if j and j["status"] in ("done", "failed", "cancelled"):
            return j
        time.sleep(0.05)
    raise AssertionError("Sammelauftrag nicht fertig")


def _plan(client, h) -> dict:
    return client.get(P, headers=h).json()


def _scenes(client, h, n: int, shots_per: int = 0) -> list[dict]:
    client.put(f"{P}/screenplay", headers=h, json={"models": {"image": "test/bild", "video": "test/video", "text": "test/text"}})
    out = []
    for i in range(n):
        sc = client.post(f"{P}/scenes", headers=h, json={"title": f"Szene {i + 1}"}).json()
        for k in range(shots_per):
            client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": f"s{i}-{k}"})
        out.append(sc)
    return out


def test_preview_counts_and_model(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.server_default_model", lambda: "server/bild")
    a, b = _scenes(client, auth_headers, 2, shots_per=2)
    _scenes(client, auth_headers, 1)                                         # Szene ohne Shots
    from backend import shots as shots_mod
    scene = shots_mod.load_scene(PROJECT_ID, a["id"])
    (ws / "bilder").mkdir(exist_ok=True)
    (ws / "bilder/x.png").write_bytes(PNG)
    scene["shots"][0]["image_rel"] = "bilder/x.png"
    scene["shots"][1].update({"image_rel": "bilder/x.png", "video_rel": "studio/media/videos/v.mp4"})
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
    assert client.get(f"{P}/batch/decompose_all", headers=auth_headers).json() == {"count": 1, "model": "test/text"}
    assert client.get(f"{P}/batch/images_all", headers=auth_headers).json() == {"count": 2, "model": "test/bild"}
    assert client.get(f"{P}/batch/videos_all", headers=auth_headers).json() == {"count": 1, "model": "test/video"}
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"image": ""}})
    assert client.get(f"{P}/batch/images_all", headers=auth_headers).json()["model"] == "server/bild"
    assert client.get(f"{P}/batch/unbekannt", headers=auth_headers).status_code == 404


def test_images_all_skips_finished_and_counts_failures(client, auth_headers, ws, monkeypatch) -> None:
    calls = []

    def provider(**kw):
        calls.append(kw)
        if len(calls) == 2:
            from backend.image_provider import ProviderError
            raise ProviderError("provider_rejected")
        return PNG
    monkeypatch.setattr("backend.image_provider.request_image", provider)
    a, b = _scenes(client, auth_headers, 2, shots_per=2)
    from backend import shots as shots_mod
    scene = shots_mod.load_scene(PROJECT_ID, a["id"])
    (ws / "bilder").mkdir(exist_ok=True)
    (ws / "bilder/x.png").write_bytes(PNG)
    scene["shots"][0]["image_rel"] = "bilder/x.png"                           # schon fertig → überspringen
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])

    r = client.post(f"{P}/batch/images_all", headers=auth_headers, json={})
    assert r.status_code == 202, r.text
    job = _wait_batch(client, auth_headers, r.json()["id"])
    assert job["status"] == "done" and job["kind"] == "images_all"
    assert (job["progress"]["total"], job["progress"]["done"], job["progress"]["failed"]) == (3, 2, 1)
    assert len(calls) == 3                                                    # ein Fehler bricht nicht ab
    shots = [s for sc in _plan(client, auth_headers)["scenes"] for s in sc["shots"]]
    assert sum(1 for s in shots if s["image_rel"]) == 3 and shots[0]["image_rel"] == "bilder/x.png"


def test_decompose_all_only_scenes_without_shots(client, auth_headers, ws) -> None:
    _scenes(client, auth_headers, 1, shots_per=1)
    _scenes(client, auth_headers, 2)
    with patch(LLM, new=AsyncMock(return_value='[{"prompt": "a"}, {"prompt": "b"}]')) as llm:
        r = client.post(f"{P}/batch/decompose_all", headers=auth_headers, json={})
        job = _wait_batch(client, auth_headers, r.json()["id"])
    assert job["status"] == "done" and job["progress"]["done"] == 2 and llm.call_count == 2
    assert [len(s["shots"]) for s in _plan(client, auth_headers)["scenes"]] == [1, 2, 2]


def test_videos_all(client, auth_headers, ws, monkeypatch) -> None:
    fake = FakeVideo()
    _install(monkeypatch, fake)
    a, = _scenes(client, auth_headers, 1, shots_per=3)
    from backend import shots as shots_mod
    scene = shots_mod.load_scene(PROJECT_ID, a["id"])
    (ws / "bilder").mkdir(exist_ok=True)
    (ws / "bilder/x.png").write_bytes(PNG)
    for s in scene["shots"][:2]:
        s["image_rel"] = "bilder/x.png"
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
    r = client.post(f"{P}/batch/videos_all", headers=auth_headers, json={})
    job = _wait_batch(client, auth_headers, r.json()["id"])
    assert job["status"] == "done" and job["progress"]["total"] == 2 and job["progress"]["done"] == 2
    assert [bool(s["video_rel"]) for s in _plan(client, auth_headers)["scenes"][0]["shots"]] == [True, True, False]


def test_one_batch_per_project_and_cancel(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(delay=0.3))
    _scenes(client, auth_headers, 1, shots_per=5)
    _scenes(client, auth_headers, 1)                                         # Szene ohne Shots: decompose_all hätte Arbeit
    r = client.post(f"{P}/batch/images_all", headers=auth_headers, json={})
    jid = r.json()["id"]
    second = client.post(f"{P}/batch/decompose_all", headers=auth_headers, json={})   # andere Art, gleiche Sperre
    assert second.status_code == 409 and second.json()["detail"]["code"] == "studio_batch_running"
    time.sleep(0.4)
    assert client.post(f"{P}/jobs/{jid}/cancel", headers=auth_headers, json={}).status_code == 200
    job = _wait_batch(client, auth_headers, jid)
    assert job["status"] == "cancelled"
    assert 1 <= job["progress"]["done"] < 5                                  # was fertig ist, bleibt
    shots = _plan(client, auth_headers)["scenes"][0]["shots"]
    assert sum(1 for s in shots if s["image_rel"]) == job["progress"]["done"]
    assert client.post(f"{P}/jobs/{'0' * 32}/cancel", headers=auth_headers, json={}).status_code == 404
    again = client.post(f"{P}/batch/images_all", headers=auth_headers, json={})   # danach wieder frei, macht mit dem Rest weiter
    assert again.status_code == 202
    assert _wait_batch(client, auth_headers, again.json()["id"])["progress"]["total"] == 5 - job["progress"]["done"]


def test_nothing_to_do(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider())
    r = client.post(f"{P}/batch/images_all", headers=auth_headers, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_batch_nothing"


def test_progress_shows_current_step(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(delay=0.4))
    sc, = _scenes(client, auth_headers, 1, shots_per=2)
    r = client.post(f"{P}/batch/images_all", headers=auth_headers, json={})
    time.sleep(0.15)
    j = {x["id"]: x for x in client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"]}[r.json()["id"]]
    assert j["status"] == "running" and j["progress"]["current"] == "Szene 1 · Shot 1"
    _wait_batch(client, auth_headers, r.json()["id"])


def test_interrupted_batch_after_restart(client, auth_headers, ws) -> None:
    from backend import jobs
    (ws / "studio/jobs").mkdir(parents=True, exist_ok=True)
    (ws / "studio/jobs" / f"{'7' * 32}.json").write_text(json.dumps(
        {"id": "7" * 32, "kind": "images_all", "target": f"batch:{PROJECT_ID}", "scene_id": "", "status": "running",
         "progress": {"total": 4, "done": 1, "failed": 0, "current": "x"}, "created_at": "2026-10-17T10:00:00Z"}))
    jobs.recover(PROJECT_ID)
    j = {x["id"]: x for x in client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"]}["7" * 32]
    assert j["status"] == "failed" and j["error"] == "interrupted"
