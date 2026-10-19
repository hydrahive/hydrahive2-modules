"""Studio C1: Medien löschen und herausfinden, wo sie benutzt werden (studio/SPEC.md „C1 im Detail“)."""
from __future__ import annotations

import json

import pytest
from _gen_helpers import PNG, P, _shot, _wait
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

pytest_plugins = ["_gen_helpers"]                 # Fixture `provider`
M = f"{MOD_PREFIX}/projects/{PROJECT_ID}/media"


def _img(ws, sub: str = "images", name: str = "a" * 32 + ".png") -> str:
    d = ws / "studio/media" / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(PNG)
    (d / f"{name}.json").write_text(json.dumps({"model": "x"}))
    return f"studio/media/{sub}/{name}"


def _first_shot(client, h, scene_id: str) -> dict:
    return next(sc for sc in client.get(P, headers=h).json()["scenes"] if sc["id"] == scene_id)["shots"][0]


def _two_variants(client, h, ws, provider):
    ole, sc, shot = _shot(client, h, ws)
    for _ in range(2):
        client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=h, json={})
        _wait(client, h, sc["id"], shot["id"])
    s = _first_shot(client, h, sc["id"])
    assert len(s["variants"]) == 2
    return ole, sc, s


def test_usage_lists_shots_clips_and_elements(client, auth_headers, ws, provider) -> None:
    ole, sc, s = _two_variants(client, auth_headers, ws, provider)
    rel = s["image_rel"]
    client.put(f"{P}/elements/{ole['id']}", headers=auth_headers, json={**ole, "references": ["bilder/ole.png", rel]})
    tl = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline", headers=auth_headers).json()
    clip = {"id": "c" * 32, "kind": "image", "start": 0, "in": 0, "out": 2, "media_rel": rel, "label": "x"}
    client.put(f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline", headers=auth_headers,
               json={"revision": tl["revision"], "fps": 25, "tracks": [{"id": "V1", "kind": "video", "clips": [clip]}]})
    u = client.get(f"{M}/usage", headers=auth_headers, params={"rel": rel}).json()
    assert u["own"] is True and u["shots"] == [{"scene_id": sc["id"], "shot_id": s["id"], "label": "Hafen · Shot 1"}]
    assert u["clips"] == 1 and u["elements"] == [{"id": ole["id"], "name": "Ole"}]
    other = s["variants"][0]
    assert client.get(f"{M}/usage", headers=auth_headers, params={"rel": other}).json()["clips"] == 0


def test_delete_chosen_variant_falls_back_to_the_other(client, auth_headers, ws, provider) -> None:
    ole, sc, s = _two_variants(client, auth_headers, ws, provider)
    chosen, other = s["image_rel"], next(v for v in s["variants"] if v != s["image_rel"])
    client.put(f"{P}/elements/{ole['id']}", headers=auth_headers, json={**ole, "references": ["bilder/ole.png", chosen]})
    r = client.delete(M, headers=auth_headers, params={"rel": chosen})
    assert r.status_code == 200 and r.json() == {"deleted": chosen}
    assert not (ws / chosen).exists() and not (ws / f"{chosen}.json").exists()
    after = _first_shot(client, auth_headers, sc["id"])
    assert after["variants"] == [other] and after["image_rel"] == other
    el = next(e for e in client.get(P, headers=auth_headers).json()["elements"] if e["id"] == ole["id"])
    assert el["references"] == ["bilder/ole.png"]
    lib = [i["rel"] for i in client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]]
    assert chosen not in lib and other in lib


def test_delete_last_image_leaves_shot_without_image(client, auth_headers, ws, provider) -> None:
    _, sc, shot = _shot(client, auth_headers, ws)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    rel = _first_shot(client, auth_headers, sc["id"])["image_rel"]
    client.delete(M, headers=auth_headers, params={"rel": rel})
    after = _first_shot(client, auth_headers, sc["id"])
    assert after["image_rel"] is None and after["variants"] == [] and after["status"] == "planned"


def test_delete_video_and_voice_clears_the_shot(client, auth_headers, ws, provider) -> None:
    _, sc, shot = _shot(client, auth_headers, ws)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    video = _img(ws, "videos", "v" * 32 + ".mp4")
    voice = _img(ws, "voice", "f" * 32 + ".mp3")
    path = ws / f"studio/scenes/{sc['id']}.json"
    data = json.loads(path.read_text())
    data["shots"][0].update(video_rel=video, voice_rel=voice, status="done")
    path.write_text(json.dumps(data))
    for rel in (video, voice):
        assert client.delete(M, headers=auth_headers, params={"rel": rel}).status_code == 200
    after = _first_shot(client, auth_headers, sc["id"])
    assert after["video_rel"] is None and after["voice_rel"] is None and after["image_rel"]   # Bild bleibt
    assert after["status"] == "done"


def test_timeline_clip_becomes_placeholder(client, auth_headers, ws) -> None:
    rel = _img(ws, "free")
    tl = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline", headers=auth_headers).json()
    clip = {"id": "c" * 32, "kind": "image", "start": 0, "in": 0, "out": 2, "media_rel": rel, "label": "Bild"}
    client.put(f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline", headers=auth_headers,
               json={"revision": tl["revision"], "fps": 25, "tracks": [{"id": "V1", "kind": "video", "clips": [clip]}]})
    client.delete(M, headers=auth_headers, params={"rel": rel})
    clips = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/timeline", headers=auth_headers).json()["tracks"][0]["clips"]
    assert len(clips) == 1 and clips[0]["missing"] is True                           # Arbeit bleibt, Lücke sichtbar


def test_delete_render_and_upload(client, auth_headers, ws) -> None:
    d = ws / "studio/renders"
    d.mkdir(parents=True)
    name = f"{'b' * 32}.mp4"
    (d / name).write_bytes(b"x")
    (d / f"{name}.json").write_text("{}")
    up = _img(ws, "uploads")
    for rel in (f"studio/renders/{name}", up):
        assert client.delete(M, headers=auth_headers, params={"rel": rel}).status_code == 200
        assert not (ws / rel).exists()
    assert client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/renders", headers=auth_headers).json()["renders"] == []


@pytest.mark.parametrize("rel", ["atelier/images/x.png", "tonstudio/clips/a.mp3", "studio/plan.json", "studio/media/../plan.json",
                                 "/etc/passwd", "studio/media/images/../../screenplay.json", "studio/scenes/x.json", ""])
def test_only_own_media(client, auth_headers, ws, rel) -> None:
    (ws / "atelier/images").mkdir(parents=True, exist_ok=True)
    (ws / "atelier/images/x.png").write_bytes(PNG)
    r = client.delete(M, headers=auth_headers, params={"rel": rel})
    assert r.status_code in (403, 404) and r.json()["detail"]["code"] in ("studio_media_not_own", "studio_media_not_found")
    assert (ws / "atelier/images/x.png").exists()
    u = client.get(f"{M}/usage", headers=auth_headers, params={"rel": "atelier/images/x.png"}).json()
    assert u["own"] is False


def test_missing_file_404(client, auth_headers, ws) -> None:
    r = client.delete(M, headers=auth_headers, params={"rel": "studio/media/images/" + "e" * 32 + ".png"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "studio_media_not_found"


def test_symlink_is_not_followed(client, auth_headers, ws) -> None:
    import os
    outside = ws.parent / "draussen.png"
    outside.write_bytes(PNG)
    (ws / "studio/media/images").mkdir(parents=True, exist_ok=True)
    os.symlink(outside, ws / "studio/media/images/link.png")
    r = client.delete(M, headers=auth_headers, params={"rel": "studio/media/images/link.png"})
    assert r.status_code in (403, 404)
    assert outside.exists()
    (ws / "studio/media/images/link.png").unlink()
    outside.unlink()


def test_busy_shot_409(client, auth_headers, ws, provider) -> None:
    """Läuft gerade ein Bild für den Shot, darf seine Datei nicht verschwinden (der Auftrag schreibt gleich hinein)."""
    _, sc, shot = _shot(client, auth_headers, ws)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    rel = _first_shot(client, auth_headers, sc["id"])["image_rel"]
    provider.delay = 1.0
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    r = client.delete(M, headers=auth_headers, params={"rel": rel})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_media_busy"
    assert (ws / rel).exists()
    _wait(client, auth_headers, sc["id"], shot["id"])


def test_foreign_project(client, auth_headers) -> None:
    o = f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/media"
    assert client.delete(o, headers=auth_headers, params={"rel": "studio/media/images/x.png"}).status_code == 404
    assert client.get(f"{o}/usage", headers=auth_headers, params={"rel": "studio/media/images/x.png"}).status_code == 404


def test_library_marks_deletable(client, auth_headers, ws) -> None:
    own = _img(ws, "free")
    (ws / "atelier/images").mkdir(parents=True, exist_ok=True)
    (ws / "atelier/images/x.png").write_bytes(PNG)
    items = {i["rel"]: i for i in client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]}
    assert items[own]["deletable"] is True and items["atelier/images/x.png"]["deletable"] is False
