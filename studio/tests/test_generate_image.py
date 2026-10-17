"""Studio 3a: Bild für einen Shot erzeugen (studio/SPEC.md „Bauplan Etappe 3“). Der Anbieter wird ersetzt."""
from __future__ import annotations

import base64
import json
import time

import pytest
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


class FakeProvider:
    """Nimmt die Anfragen an den Bild-Anbieter entgegen (statt OpenRouter)."""

    def __init__(self, result=PNG, error: str | None = None, delay: float = 0.0):
        self.calls: list[dict] = []
        self.result, self.error, self.delay = result, error, delay

    def __call__(self, **kw):
        self.calls.append(kw)
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            from backend.image_provider import ProviderError
            raise ProviderError(self.error)
        return self.result


@pytest.fixture
def provider(monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr("backend.image_provider.request_image", fake)
    return fake


def _wait(client, h, sid: str, shot_id: str, timeout: float = 5.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        r = client.get(f"{P}/jobs", headers=h)
        jobs = [j for j in r.json()["jobs"] if j["target"] == shot_id]
        if jobs and jobs[0]["status"] in ("done", "failed"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Auftrag nicht fertig geworden")


def _shot(client, h, ws, with_ref: bool = True) -> tuple[dict, dict, dict]:
    client.put(f"{P}/screenplay", headers=h, json={"aspect_ratio": "9:16", "look": {"style": "film noir", "palette": ["#111"]},
                                                     "models": {"image": "test/billig"}})
    refs = []
    if with_ref:
        (ws / "bilder").mkdir(exist_ok=True)
        (ws / "bilder/ole.png").write_bytes(PNG)
        refs = ["bilder/ole.png"]
    ole = client.post(f"{P}/elements", headers=h, json={"kind": "character", "name": "Ole", "description": "alter Fischer",
                                                       "style_anchor": "yellow raincoat", "references": refs}).json()
    sc = client.post(f"{P}/scenes", headers=h, json={"title": "Hafen", "element_ids": [ole["id"]],
                                                    "camera": {"light": "golden_hour", "weather": "rain"}}).json()
    shot = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": "boat enters harbour", "shot": "wide",
                                                                         "element_ids": [ole["id"]]}).json()
    return ole, sc, shot


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


def test_running_job_after_restart_is_marked_failed(client, auth_headers, ws) -> None:
    from backend import jobs
    (ws / "studio/jobs").mkdir(parents=True, exist_ok=True)
    (ws / "studio/jobs/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json").write_text(json.dumps(
        {"id": "a" * 32, "kind": "image", "target": "b" * 32, "scene_id": "c" * 32, "status": "running"}))
    jobs.recover(PROJECT_ID)
    got = client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"]
    assert got[0]["status"] == "failed" and got[0]["error"] == "interrupted"


def test_references_only_of_shot_elements_and_real_images(client, auth_headers, ws, provider) -> None:
    """Referenzen: nur Bausteine des Shots, nur echte Bilddateien im Projekt (keine Verknüpfungen nach draußen)."""
    import os
    ole, sc, shot = _shot(client, auth_headers, ws)
    (ws / "bilder/mira.png").write_bytes(PNG)
    mira = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Mira", "references": ["bilder/mira.png"]}).json()
    client.put(f"{P}/scenes/{sc['id']}", headers=auth_headers, json={"element_ids": [ole["id"], mira["id"]]})   # Mira in der Szene, nicht im Shot
    # Referenz nachträglich durch eine Verknüpfung nach draußen ersetzen (Datei wurde nach dem Speichern getauscht)
    outside = ws.parent / "draussen.png"
    outside.write_bytes(PNG)
    (ws / "bilder/ole.png").unlink()
    os.symlink(outside, ws / "bilder/ole.png")
    client.post(f"{P}/scenes/{sc['id']}/shots/{shot['id']}/image", headers=auth_headers, json={})
    assert _wait(client, auth_headers, sc["id"], shot["id"])["status"] == "done"
    assert provider.calls[0]["references"] == []                     # Ole: Symlink → raus; Mira: nicht im Shot → raus
    (ws / "bilder/ole.png").unlink()
    outside.unlink()


def test_too_big_is_not_an_image(monkeypatch) -> None:
    from backend import image_provider
    monkeypatch.setattr(image_provider, "MAX_BYTES", 100)
    assert image_provider.image_kind(PNG) == "png"
    assert image_provider.image_kind(PNG + b"\0" * 200) is None
    assert image_provider.image_kind(b"\xff\xd8\xff\xe0abc") == "jpg"
    assert image_provider.image_kind(b"RIFF\0\0\0\0WEBPVP8 ") == "webp"


def test_variants_only_from_studio_media(client, auth_headers, ws) -> None:
    from backend import shots as shots_mod
    _, sc, shot = _shot(client, auth_headers, ws, with_ref=False)
    scene = shots_mod.load_scene(PROJECT_ID, sc["id"])
    scene["shots"][0]["variants"] = ["studio/media/images/ok.png", "../../etc/passwd", "atelier/images/x.png",
                                     "studio/media/images/../../x.png", 5]
    saved = shots_mod.save_shots(PROJECT_ID, scene, scene["shots"])[0]
    assert saved["variants"] == ["studio/media/images/ok.png"]
