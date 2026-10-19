"""Studio Bauplan L – lokal erzeugen (studio/SPEC.md). Der Kern-Weg (ComfyUI) wird ersetzt; kein Netzverkehr."""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from _draft_helpers import D
from _gen_helpers import PNG, P

from backend import image_provider

MODEL = "local:wks/flux2-klein-image"


@dataclass(frozen=True)
class _Params:                                         # Ersatz für hydrahive.llm.video_backends.VideoParams
    prompt: str
    width: int = 1280
    height: int = 720
    aspect_ratio: str = "16:9"
    seed: int | None = None
    image_url: str | None = None
    references: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _OldParams:                                      # Kern ohne Vorlagen-Liste (vor dem Kern-PR)
    prompt: str
    width: int = 1280
    height: int = 720
    aspect_ratio: str = "16:9"
    seed: int | None = None
    image_url: str | None = None


class FakeLocal:
    """Ersetzt resolve_local_workflow + run_local_media des Kerns."""

    def __init__(self, result: bytes | None = PNG, error: Exception | None = None, resolve_error: Exception | None = None):
        self.calls: list[dict] = []
        self.result, self.error, self.resolve_error = result, error, resolve_error

    def resolve(self, model, config, category):
        if self.resolve_error:
            raise self.resolve_error
        self.category = category
        return "backend", {"id": "wks"}

    async def run(self, backend, provider, model, params, dest, *, timeout):
        self.calls.append({"model": model, "params": params, "timeout": timeout, "dest": dest})
        if self.error:
            raise self.error
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / "bild.png"
        out.write_bytes(self.result or b"")
        return out


@pytest.fixture
def local(monkeypatch):
    fake = FakeLocal()
    monkeypatch.setattr(image_provider, "_local_parts", lambda: (fake.resolve, fake.run, _Params, dict))
    return fake


def _uri(b: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(b).decode()


# --- L1 Weg über den Kern --------------------------------------------------------------------------------------------

def test_l1_local_model_goes_to_core_not_openrouter(local, monkeypatch) -> None:
    monkeypatch.setattr(image_provider.httpx, "post", lambda *a, **k: pytest.fail("OpenRouter gefragt"))
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "", raising=False)
    raw = image_provider.request_image(model=MODEL, prompt="Hydra im Wald", references=[_uri(b"A"), _uri(b"B")],
                                       aspect_ratio="16:9", seed=42)
    assert raw == PNG
    p = local.calls[0]["params"]
    assert local.category == "image" and local.calls[0]["model"] == MODEL
    assert p.prompt == "Hydra im Wald" and p.seed == 42 and p.aspect_ratio == "16:9"
    assert p.references == [_uri(b"A"), _uri(b"B")]                                  # Reihenfolge bleibt


@pytest.mark.parametrize("aspect,size", [("16:9", (1360, 768)), ("9:16", (768, 1360)), ("1:1", (768, 768)),
                                         ("4:3", (1024, 768)), ("21:9", (1792, 768)), ("auto", (768, 768))])
def test_l1_size_from_aspect(local, aspect, size) -> None:
    image_provider.request_image(model=MODEL, prompt="x", references=[], aspect_ratio=aspect)
    p = local.calls[0]["params"]
    assert (p.width, p.height) == size and p.width % 16 == 0 and p.height % 16 == 0


def test_l1_at_most_three_references(local) -> None:
    image_provider.request_image(model=MODEL, prompt="x", references=[_uri(bytes([i])) for i in range(5)], aspect_ratio="1:1")
    assert len(local.calls[0]["params"].references) == 3


def test_l1_temp_files_are_removed(local) -> None:
    image_provider.request_image(model=MODEL, prompt="x", references=[], aspect_ratio="1:1")
    assert not Path(local.calls[0]["dest"]).exists()


@pytest.mark.parametrize("fake,code", [
    (FakeLocal(resolve_error=ValueError("Kein Workflow")), "provider_rejected"),
    (FakeLocal(error=RuntimeError("Netzwerk-Fehler")), "provider_unreachable"),
    (FakeLocal(error=TimeoutError("zu lange")), "provider_unreachable"),
    (FakeLocal(error=OSError("Platte")), "provider_unreachable"),
    (FakeLocal(result=b""), "empty_answer"),
])
def test_l1_errors_have_codes(monkeypatch, fake, code) -> None:
    monkeypatch.setattr(image_provider, "_local_parts", lambda: (fake.resolve, fake.run, _Params, dict))
    with pytest.raises(image_provider.ProviderError) as e:
        image_provider.request_image(model=MODEL, prompt="x", references=[], aspect_ratio="1:1")
    assert str(e.value) == code


def test_l1_cloud_model_still_openrouter(monkeypatch) -> None:
    monkeypatch.setattr(image_provider, "_local_parts", lambda: pytest.fail("lokal gefragt"))
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "", raising=False)
    with pytest.raises(image_provider.ProviderError) as e:
        image_provider.request_image(model="openai/gpt-5-image", prompt="x", references=[], aspect_ratio="1:1")
    assert str(e.value) == "no_key"


def test_l1_real_core_parts_exist() -> None:
    resolve, run, params, cfg = image_provider._local_parts()
    assert params(prompt="x").prompt == "x" and callable(resolve) and callable(run) and callable(cfg)


def test_l1_first_reference_also_as_image_url(local) -> None:
    image_provider.request_image(model=MODEL, prompt="x", references=[_uri(b"A"), _uri(b"B")], aspect_ratio="1:1")
    assert local.calls[0]["params"].image_url == _uri(b"A")
    image_provider.request_image(model=MODEL, prompt="x", references=[], aspect_ratio="1:1")
    assert local.calls[1]["params"].image_url is None


def test_l1_older_core_gets_only_the_first_reference(monkeypatch) -> None:
    fake = FakeLocal()
    monkeypatch.setattr(image_provider, "_local_parts", lambda: (fake.resolve, fake.run, _OldParams, dict))
    image_provider.request_image(model=MODEL, prompt="x", references=[_uri(b"A"), _uri(b"B")], aspect_ratio="1:1")
    p = fake.calls[0]["params"]
    assert p.image_url == _uri(b"A") and not hasattr(p, "references")


def test_l1_shot_image_with_local_model(client, auth_headers, ws, local) -> None:
    client.put(f"{P}/screenplay", headers=auth_headers, json={"models": {"image": MODEL}, "aspect_ratio": "9:16"})
    (ws / "fotos").mkdir(exist_ok=True)
    (ws / "fotos/h.png").write_bytes(PNG)
    h = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Hydra", "references": ["fotos/h.png"]}).json()
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Wald"}).json()
    sh = client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "Hydra im Wald", "element_ids": [h["id"]]}).json()
    assert client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/image", headers=auth_headers, json={}).status_code == 202
    end = time.time() + 5
    while time.time() < end and not local.calls:
        time.sleep(0.05)
    for _ in range(100):
        job = [j for j in client.get(f"{P}/jobs", headers=auth_headers).json()["jobs"] if j["target"] == sh["id"]][0]
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.05)
    assert job["status"] == "done", job
    p = local.calls[0]["params"]
    assert p.seed == h["seed"] and p.references == [_uri(PNG)] and (p.width, p.height) == (768, 1360)
    meta = json.loads(next((ws / "studio/media/images").glob("*.json")).read_text())
    assert meta["model"] == MODEL


# --- L3 Drehbuch-Antwort einmal wiederholen ---------------------------------------------------------------------------

def _good() -> str:
    return json.dumps({"title": "T", "logline": "L", "elements": [{"key": "h", "kind": "character", "name": "Hydra"}],
                       "scenes": [{"title": "S", "description": "d", "element_keys": ["h"],
                                   "shots": [{"shot": "wide", "prompt": "p", "element_keys": ["h"], "duration": 4}]}]})


def test_l3_unusable_answer_is_asked_again_once(client, auth_headers, ws) -> None:
    llm = AsyncMock(side_effect=[_good()[:-3], _good()])                            # erste Antwort abgeschnitten
    with patch("backend.draft_idea.llm_client.complete", new=llm):
        r = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "x", "length": "30"})
    assert r.status_code == 200, r.text
    assert llm.await_count == 2 and r.json()["draft"]["head"]["title"] == "T"


def test_l3_two_unusable_answers_give_the_error(client, auth_headers, ws) -> None:
    llm = AsyncMock(side_effect=["kaputt", '{"scenes": []}', _good()])
    with patch("backend.draft_idea.llm_client.complete", new=llm):
        r = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "x", "length": "30"})
    assert r.status_code == 502 and r.json()["detail"]["code"] == "studio_idea_failed"
    assert llm.await_count == 2


def test_l3_llm_error_is_not_repeated(client, auth_headers, ws) -> None:
    llm = AsyncMock(side_effect=RuntimeError("down"))
    with patch("backend.draft_idea.llm_client.complete", new=llm):
        r = client.post(f"{D}/idea", headers=auth_headers, json={"idea": "x", "length": "30"})
    assert r.status_code == 502 and llm.await_count == 1

