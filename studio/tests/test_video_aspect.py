"""Studio: Video-Format an das Modell anpassen wie die Dauer (gemessen 17.10.: google/veo-3.1 kann nur 16:9 und 9:16,
x-ai/grok-imagine-video-1.5-lite 16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3)."""
from __future__ import annotations

import httpx
import pytest


class Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return {"data": self._data}


class Client:
    def __init__(self, data, calls):
        self.data, self.calls = data, calls

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, headers=None):
        self.calls.append(url)
        return Resp(self.data)


MODELS = [
    {"id": "google/veo-3.1", "supported_durations": [4, 6, 8], "supported_aspect_ratios": ["16:9", "9:16"]},
    {"id": "x-ai/grok-lite", "supported_durations": [1, 2, 3], "supported_aspect_ratios": ["16:9", "9:16", "1:1", "4:3"]},
    {"id": "ohne/angaben"},
]


@pytest.fixture
def listing(monkeypatch):
    from backend import video_provider
    calls: list = []
    video_provider._durations_cache.clear()
    video_provider._aspects_cache.clear()
    monkeypatch.setattr(video_provider, "_key", lambda: "k")
    monkeypatch.setattr(httpx, "Client", lambda timeout=None: Client(MODELS, calls))
    yield calls
    video_provider._durations_cache.clear()
    video_provider._aspects_cache.clear()


@pytest.mark.parametrize(("model", "wanted", "expected"), [
    ("google/veo-3.1", "1:1", "16:9"),        # gleich weit → das breitere Bild (Film)
    ("google/veo-3.1", "4:3", "16:9"),
    ("google/veo-3.1", "9:16", "9:16"),
    ("google/veo-3.1", "21:9", "16:9"),
    ("x-ai/grok-lite", "1:1", "1:1"),
    ("x-ai/grok-lite", "21:9", "16:9"),
    ("ohne/angaben", "21:9", "21:9"),         # unbekannt → unverändert
    ("gibt/es-nicht", "1:1", "1:1"),
])
def test_aspect_fits_the_model(listing, model, wanted, expected) -> None:
    from backend import video_provider
    assert video_provider.fit_aspect(model, wanted) == expected


def test_listing_is_asked_once_for_duration_and_format(listing) -> None:
    from backend import video_provider
    video_provider.allowed_durations("google/veo-3.1")
    video_provider.fit_aspect("google/veo-3.1", "1:1")
    video_provider.fit_aspect("x-ai/grok-lite", "1:1")
    assert len(listing) == 1


def test_job_sends_the_fitted_format(client, auth_headers, ws, monkeypatch) -> None:
    """Der Auftrag schickt das angepasste Format an den Anbieter (nicht das des Drehbuchs)."""
    from _video_helpers import FakeVideo, _install
    from backend import video_provider
    fake = FakeVideo()
    _install(monkeypatch, fake)
    monkeypatch.setattr(video_provider, "fit_aspect", lambda model, ar: "16:9" if ar == "1:1" else ar)
    from _gen_helpers import P, PNG
    client.put(f"{P}/screenplay", headers=auth_headers, json={"aspect_ratio": "1:1", "models": {"video": "google/veo-3.1"}})
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "S"}).json()
    sh = client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "p", "duration": 4}).json()
    img = ws / "studio/media/images/a.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(PNG)
    import json as _j
    f = ws / "studio/scenes" / f"{sc['id']}.json"
    data = _j.loads(f.read_text())
    data["shots"][0]["image_rel"] = "studio/media/images/a.png"
    f.write_text(_j.dumps(data))
    r = client.post(f"{P}/scenes/{sc['id']}/shots/{sh['id']}/video", headers=auth_headers, json={})
    assert r.status_code == 202, r.text
    import threading
    for t in threading.enumerate():
        if t.name.startswith("studio-"):
            t.join(5)
    submit = [kw for step, kw in fake.calls if step == "submit"]
    assert submit and submit[0]["aspect_ratio"] == "16:9"
