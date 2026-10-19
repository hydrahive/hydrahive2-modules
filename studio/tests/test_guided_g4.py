"""Studio G4: Bewegung im geführten Weg – Standbild statt Clip (studio/SPEC.md „Bauplan G4“). Anbieter ersetzt."""
from __future__ import annotations

import time

from _gen_helpers import PNG, P, _wait
from conftest import PROJECT_ID

pytest_plugins = ["_gen_helpers", "_video_helpers"]


def _scenes(client, h, ws, n: int = 2) -> list[tuple[str, str]]:
    """n Szenen mit je einem Shot, der schon ein Bild hat."""
    from backend import shots as shots_mod
    (ws / "bilder").mkdir(exist_ok=True)
    (ws / "bilder/b.png").write_bytes(PNG)
    client.put(f"{P}/screenplay", headers=h, json={"models": {"video": "test/video"}})
    out = []
    for i in range(n):
        sc = client.post(f"{P}/scenes", headers=h, json={"title": f"S{i}"}).json()
        shot = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": f"p{i}", "duration": 4}).json()
        scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
        scene["shots"][0].update({"image_rel": "bilder/b.png", "status": "image_ready"})
        shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
        out.append((sc["id"], shot["id"]))
    return out


def _shot(client, h, sid: str) -> dict:
    return next(s for s in client.get(P, headers=h).json()["scenes"] if s["id"] == sid)["shots"][0]


def test_still_flag(client, auth_headers, ws) -> None:
    (sid, xid), = _scenes(client, auth_headers, ws, 1)
    assert _shot(client, auth_headers, sid)["still"] is False
    r = client.put(f"{P}/scenes/{sid}/shots/{xid}", headers=auth_headers, json={"still": True})
    assert r.status_code == 200 and r.json()["still"] is True
    assert client.put(f"{P}/scenes/{sid}/shots/{xid}", headers=auth_headers, json={"still": "ja"}).json()["still"] is False


def test_batch_skips_stills(client, auth_headers, ws, video) -> None:
    (s1, x1), (s2, _) = _scenes(client, auth_headers, ws, 2)
    client.put(f"{P}/scenes/{s1}/shots/{x1}", headers=auth_headers, json={"still": True})
    assert client.get(f"{P}/batch/videos_all", headers=auth_headers).json()["count"] == 1
    job = client.post(f"{P}/batch/videos_all", headers=auth_headers).json()
    end = time.time() + 10
    while time.time() < end:
        j = next(x for x in client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"] if x["id"] == job["id"])
        if j["status"] == "done":
            break
        time.sleep(0.05)
    assert j["progress"]["total"] == 1
    assert _shot(client, auth_headers, s1)["video_rel"] is None
    assert _shot(client, auth_headers, s2)["video_rel"]


def test_all_stills_means_nothing_to_do(client, auth_headers, ws, video) -> None:
    (s1, x1), = _scenes(client, auth_headers, ws, 1)
    client.put(f"{P}/scenes/{s1}/shots/{x1}", headers=auth_headers, json={"still": True})
    r = client.post(f"{P}/batch/videos_all", headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_batch_nothing"


def test_single_video_ends_still(client, auth_headers, ws, video) -> None:
    (sid, xid), = _scenes(client, auth_headers, ws, 1)
    client.put(f"{P}/scenes/{sid}/shots/{xid}", headers=auth_headers, json={"still": True})
    assert client.post(f"{P}/scenes/{sid}/shots/{xid}/video", headers=auth_headers).status_code == 202
    assert _wait(client, auth_headers, sid, xid)["status"] == "done"
    s = _shot(client, auth_headers, sid)
    assert s["video_rel"] and s["still"] is False


def test_failed_video_keeps_still(client, auth_headers, ws, monkeypatch) -> None:
    from _video_helpers import FakeVideo, _install
    _install(monkeypatch, FakeVideo(fail_at="submit"))
    (sid, xid), = _scenes(client, auth_headers, ws, 1)
    client.put(f"{P}/scenes/{sid}/shots/{xid}", headers=auth_headers, json={"still": True})
    client.post(f"{P}/scenes/{sid}/shots/{xid}/video", headers=auth_headers)
    assert _wait(client, auth_headers, sid, xid)["status"] == "failed"
    assert _shot(client, auth_headers, sid)["still"] is True


def test_drop_video_falls_back_to_image(client, auth_headers, ws, video) -> None:
    (sid, xid), = _scenes(client, auth_headers, ws, 1)
    client.post(f"{P}/scenes/{sid}/shots/{xid}/video", headers=auth_headers)
    _wait(client, auth_headers, sid, xid)
    rel = _shot(client, auth_headers, sid)["video_rel"]
    from conftest import MOD_PREFIX
    r = client.request("DELETE", f"{MOD_PREFIX}/projects/{PROJECT_ID}/media", headers=auth_headers, params={"rel": rel})
    assert r.status_code == 200
    s = _shot(client, auth_headers, sid)
    assert s["video_rel"] is None and s["image_rel"] == "bilder/b.png"
