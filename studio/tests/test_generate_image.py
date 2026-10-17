"""Studio 3a: Bild für einen Shot erzeugen (studio/SPEC.md „Bauplan Etappe 3“). Der Anbieter wird ersetzt."""
from __future__ import annotations

import json
import time

from _gen_helpers import PNG, FakeProvider, P, _shot, _wait
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

pytest_plugins = ["_gen_helpers"]                 # Fixture `provider`


def test_generate_image_for_shot(client, auth_headers, ws, provider) -> None:
    _, sc, shot = _shot(client, auth_headers, ws)
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    assert r.status_code == 202, r.text
    assert r.json()["status"] in ("queued", "running") and r.json()["kind"] == "image"
    job = _wait(client, auth_headers, sc["id"], shot["id"])
    assert job["status"] == "done", job

    call = provider.calls[0]
    assert call["model"] == "test/billig" and call["aspect_ratio"] == "9:16"     # aus dem Drehbuch
    for needle in ("film noir", "Ole: alter Fischer", "yellow raincoat", "boat enters harbour", "wide establishing shot",
                   "golden hour", "rain"):
        assert needle in call["prompt"], needle
    assert len(call["references"]) == 1 and call["references"][0].startswith("data:image/png;base64,")

    saved = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert saved["status"] == "image_ready"
    assert saved["image_rel"].startswith("studio/media/images/") and saved["image_rel"].endswith(".png")
    assert (ws / saved["image_rel"]).read_bytes() == PNG
    assert saved["variants"] == [saved["image_rel"]]
    meta = json.loads((ws / (saved["image_rel"] + ".json")).read_text())
    assert meta["model"] == "test/billig" and meta["shot_id"] == shot["id"] and "boat enters harbour" in meta["prompt"]

    lib = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]
    mine = [i for i in lib if i["rel"] == saved["image_rel"]]
    assert mine and mine[0]["source"] == "studio" and mine[0]["kind"] == "image" and mine[0]["origin"] == "ai"


def test_default_model_of_server_when_screenplay_has_none(client, auth_headers, ws, provider, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.server_default_model", lambda: "server/standard")
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"image": ""}})
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    assert _wait(client, auth_headers, sc["id"], shot["id"])["status"] == "done"
    assert provider.calls[0]["model"] == "server/standard" and provider.calls[0]["references"] == []


def test_variants_and_choose(client, auth_headers, ws, provider) -> None:
    _, sc, shot = _shot(client, auth_headers, ws)
    U = f"{P}/scenes/{sc['id']}/shots/{shot['id']}"
    for _ in range(2):
        client.post(f"{U}/image", headers=auth_headers, json={})
        _wait(client, auth_headers, sc["id"], shot["id"])
        time.sleep(0.05)
    s = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert len(s["variants"]) == 2 and s["image_rel"] == s["variants"][-1]           # neuestes ist gewählt
    r = client.put(f"{U}/variant", headers=auth_headers, json={"image_rel": s["variants"][0]})
    assert r.status_code == 200 and r.json()["image_rel"] == s["variants"][0]
    assert client.put(f"{U}/variant", headers=auth_headers, json={"image_rel": "bilder/ole.png"}).status_code == 400
    assert client.put(f"{U}/variant", headers=auth_headers, json={"image_rel": "../x.png"}).status_code == 400


def test_at_most_8_variants_oldest_drops_out(client, auth_headers, ws, provider) -> None:
    from backend import shots as shots_mod
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    scene["shots"][0]["variants"] = [f"studio/media/images/v{i}.png" for i in range(8)]
    shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    _wait(client, auth_headers, sc["id"], shot["id"])
    v = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]["variants"]
    assert len(v) == 8 and "studio/media/images/v0.png" not in v and v[0] == "studio/media/images/v1.png"


def test_provider_error_is_clear_and_shot_unchanged(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(error="no_key"))
    _, sc, shot = _shot(client, auth_headers, ws)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    job = _wait(client, auth_headers, sc["id"], shot["id"])
    assert job["status"] == "failed" and job["error"] == "no_key"                    # Code, Text macht das Frontend
    s = client.get(P, headers=auth_headers).json()["scenes"][0]["shots"][0]
    assert s["status"] == "planned" and s["image_rel"] is None


def test_not_an_image_is_rejected(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(result=b"<html>kaputt</html>"))
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    job = _wait(client, auth_headers, sc["id"], shot["id"])
    assert job["status"] == "failed" and job["error"] == "bad_image"
    assert not list((ws / "studio").glob("media/images/*"))


def test_one_job_per_shot(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(delay=0.5))
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    U = f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image"
    assert client.post(U, headers=auth_headers, json={}).status_code == 202
    r = client.post(U, headers=auth_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_job_running"
    _wait(client, auth_headers, sc["id"], shot["id"])
    assert client.post(U, headers=auth_headers, json={}).status_code == 202          # danach wieder frei
    _wait(client, auth_headers, sc["id"], shot["id"])


def test_ids_and_members(client, auth_headers, other_headers, ws, provider) -> None:
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    assert client.post(f"{P}/scenes/{sc['id']}/shots/{'a' * 32}/image", headers=auth_headers, json={}).status_code == 404
    assert client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=other_headers, json={}).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/jobs", headers=auth_headers).status_code == 404
    assert provider.calls == []
