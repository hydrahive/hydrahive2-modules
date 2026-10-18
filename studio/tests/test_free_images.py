"""Studio B3: freie Bilder ohne Shot (studio/SPEC.md „Bauplan B3“). Der Anbieter wird ersetzt."""
from __future__ import annotations

import json
import time

from _gen_helpers import PNG, FakeProvider, P
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

pytest_plugins = ["_gen_helpers"]                 # Fixture `provider`
F = f"{P}/free-images"


def _wait_free(client, h, timeout: float = 10.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["kind"] == "free_images"]
        if jobs and jobs[0]["status"] in ("done", "failed", "cancelled"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Auftrag nicht fertig geworden")


def test_free_images_with_screenplay_defaults(client, auth_headers, ws, provider) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"aspect_ratio": "9:16", "models": {"image": "test/billig"}})
    (ws / "bilder").mkdir()
    (ws / "bilder/ref.png").write_bytes(PNG)
    r = client.post(F, headers=auth_headers, json={"prompt": "a red kite over the dunes", "count": 3,
                                                   "references": ["bilder/ref.png", "../ausserhalb.png", "fehlt.png"]})
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "free_images" and r.json()["progress"]["total"] == 3
    job = _wait_free(client, auth_headers)
    assert job["status"] == "done" and job["progress"]["done"] == 3 and job["progress"]["failed"] == 0
    assert len(provider.calls) == 3
    call = provider.calls[0]
    assert call["model"] == "test/billig" and call["aspect_ratio"] == "9:16" and call["prompt"] == "a red kite over the dunes"
    assert len(call["references"]) == 1 and call["references"][0].startswith("data:image/png;base64,")   # nur echte Projektbilder
    rels = job["result"]["images"]
    assert len(rels) == 3 and all(x.startswith("studio/media/free/") and x.endswith(".png") for x in rels)
    meta = json.loads((ws / (rels[0] + ".json")).read_text())
    assert meta["prompt"] == "a red kite over the dunes" and meta["model"] == "test/billig" and meta["aspect_ratio"] == "9:16"
    lib = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]
    free = [i for i in lib if i["rel"] in rels]
    assert len(free) == 3 and all(i["source"] == "studio_free" and i["kind"] == "image" and i["origin"] == "ai" for i in free)
    assert free[0]["prompt"] == "a red kite over the dunes"
    assert not (ws / "studio" / "scenes").exists()                                    # kein Shot, keine Szene


def test_own_model_and_format(client, auth_headers, ws, provider) -> None:
    r = client.post(F, headers=auth_headers, json={"prompt": "x", "count": 1, "model": "andere/marke", "aspect_ratio": "1:1"})
    assert r.status_code == 202
    _wait_free(client, auth_headers)
    assert provider.calls[0]["model"] == "andere/marke" and provider.calls[0]["aspect_ratio"] == "1:1"


def test_one_failure_does_not_stop_the_rest(client, auth_headers, ws, monkeypatch) -> None:
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 2:
            from backend.image_provider import ProviderError
            raise ProviderError("provider_rejected")
        return PNG
    monkeypatch.setattr("backend.image_provider.request_image", flaky)
    client.post(F, headers=auth_headers, json={"prompt": "x", "count": 3})
    job = _wait_free(client, auth_headers)
    assert job["status"] == "done" and job["progress"]["done"] == 2 and job["progress"]["failed"] == 1
    assert len(job["result"]["images"]) == 2 and job["result"]["errors"] == ["provider_rejected"]


def test_all_failed_is_failed(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(error="no_key"))
    client.post(F, headers=auth_headers, json={"prompt": "x", "count": 2})
    job = _wait_free(client, auth_headers)
    assert job["status"] == "failed" and job["error"] == "no_key"


def test_bad_input(client, auth_headers, provider) -> None:
    for body in ({"prompt": "", "count": 1}, {"prompt": "x" * 2001, "count": 1}, {"prompt": "x", "count": 0},
                 {"prompt": "x", "count": 5}, {"prompt": "x", "count": "2"}, {"prompt": "x", "count": True}, {"prompt": "x", "count": 1, "aspect_ratio": "7:3"},
                 {"prompt": "x", "count": 1, "references": "a.png"}, {"prompt": "x", "count": 1, "model": "m" * 201}):
        r = client.post(F, headers=auth_headers, json=body)
        assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_free_invalid", body
    assert provider.calls == []


def test_only_one_free_job_at_a_time(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.image_provider.request_image", FakeProvider(delay=0.4))
    assert client.post(F, headers=auth_headers, json={"prompt": "x", "count": 1}).status_code == 202
    r = client.post(F, headers=auth_headers, json={"prompt": "y", "count": 1})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "studio_free_running"
    _wait_free(client, auth_headers)


def test_foreign_project(client, auth_headers, provider) -> None:
    r = client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/plan/free-images", headers=auth_headers, json={"prompt": "x", "count": 1})
    assert r.status_code == 404 and provider.calls == []


def test_references_only_real_project_images(client, auth_headers, ws, provider) -> None:
    """Keine Nicht-Bilder, keine Symlinks – auch wenn die Datei im Projekt liegt."""
    (ws / "bilder").mkdir()
    (ws / "bilder/echt.png").write_bytes(PNG)
    (ws / "bilder/notiz.txt").write_text("geheim")
    (ws / "bilder/link.png").symlink_to(ws / "bilder/echt.png")
    client.post(F, headers=auth_headers, json={"prompt": "x", "count": 1, "references": ["bilder/notiz.txt", "bilder/link.png"]})
    _wait_free(client, auth_headers)
    assert provider.calls[0]["references"] == []
