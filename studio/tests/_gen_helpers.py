"""Gemeinsame Hilfen der 3a-Tests (Anbieter-Ersatz, Shot anlegen, auf Auftrag warten)."""

from __future__ import annotations

import base64
import time

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

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


