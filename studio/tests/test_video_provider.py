"""Studio 3b: der echte Video-Aufruf (OpenRouter), mit ersetztem Netz. Schutz vor Schlüssel-Leck und zu großen Dateien."""
from __future__ import annotations

import httpx
import pytest

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\0" * 64


@pytest.fixture
def vp(monkeypatch):
    from backend import video_provider
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "k")
    monkeypatch.setattr(video_provider, "POLL_INTERVAL", 0.0)
    return video_provider


_REAL_CLIENT = httpx.Client                                # vor jedem Ersatz festhalten


def _client(monkeypatch, handler):
    """httpx.Client durch einen mit fester Antwort ersetzen (jeder Aufruf ersetzt den vorigen, nicht verschachtelt)."""
    def make(*a, **k):
        k["transport"] = httpx.MockTransport(handler)
        return _REAL_CLIENT(*a, **k)
    monkeypatch.setattr(httpx, "Client", make)


def test_submit_payload_and_no_key(vp, monkeypatch) -> None:
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        return httpx.Response(200, json={"id": "job-7"})
    _client(monkeypatch, handler)
    rid = vp.submit_video(model="m", prompt="p", image_url="data:image/png;base64,AA", duration=5, aspect_ratio="9:16")
    assert rid == "job-7"
    body = __import__("json").loads(seen[0].content)
    assert body["frame_images"] == [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AA"}, "frame_type": "first_frame"}]
    assert body["duration"] == 5 and body["aspect_ratio"] == "9:16" and seen[0].headers["Authorization"] == "Bearer k"
    monkeypatch.setattr("hydrahive.llm._config.openrouter_key", lambda: "")
    with pytest.raises(vp.ProviderError, match="no_key"):
        vp.submit_video(model="m", prompt="p", image_url="x", duration=5, aspect_ratio="16:9")
    assert len(seen) == 1                                                    # ohne Schlüssel kein Netzaufruf


def test_submit_rejected(vp, monkeypatch) -> None:
    _client(monkeypatch, lambda req: httpx.Response(400, json={"error": {"message": "bad model"}}))
    with pytest.raises(vp.ProviderError, match="provider_rejected"):
        vp.submit_video(model="m", prompt="p", image_url="x", duration=5, aspect_ratio="16:9")


def test_wait_until_done_failed_and_timeout(vp, monkeypatch) -> None:
    states = [{"status": "pending"}, {"status": "processing"}, {"status": "completed", "unsigned_urls": ["https://cdn.example/a.mp4"]}]
    seen = []
    _client(monkeypatch, lambda req: (seen.append(req), httpx.Response(200, json=states[min(len(seen) - 1, 2)]))[1])
    assert vp.wait_for_video("job-7", duration=5) == "https://cdn.example/a.mp4" and len(seen) == 3
    _client(monkeypatch, lambda req: httpx.Response(200, json={"status": "failed", "error": "content policy"}))
    with pytest.raises(vp.ProviderError, match="video_failed"):
        vp.wait_for_video("job-7", duration=5)
    _client(monkeypatch, lambda req: httpx.Response(200, json={"status": "completed"}))
    with pytest.raises(vp.ProviderError, match="empty_answer"):
        vp.wait_for_video("job-7", duration=5)
    monkeypatch.setattr(vp, "poll_budget", lambda duration: 0.0)
    _client(monkeypatch, lambda req: httpx.Response(200, json={"status": "processing"}))
    with pytest.raises(vp.ProviderError, match="timeout"):
        vp.wait_for_video("job-7", duration=5)


def test_poll_budget_grows_with_duration_and_is_capped(vp) -> None:
    assert vp.poll_budget(5) < vp.poll_budget(20) <= vp.POLL_CAP
    assert vp.poll_budget(10_000) == vp.POLL_CAP


def test_download_key_only_to_openrouter_and_size_limit(vp, monkeypatch, tmp_path) -> None:
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        return httpx.Response(200, content=MP4)
    _client(monkeypatch, handler)
    dest = tmp_path / "a.mp4"
    vp.download_video("https://cdn.example/a.mp4", dest)
    assert dest.read_bytes() == MP4 and "Authorization" not in seen[-1].headers    # fremder Speicher: kein Schlüssel
    vp.download_video("https://openrouter.ai/api/v1/videos/job-7/content", dest)
    assert seen[-1].headers["Authorization"] == "Bearer k"
    with pytest.raises(vp.ProviderError, match="bad_url"):
        vp.download_video("http://cdn.example/a.mp4", dest)                      # nur https
    dest.unlink()
    monkeypatch.setattr(vp, "MAX_BYTES", 20)
    with pytest.raises(vp.ProviderError, match="too_big"):
        vp.download_video("https://cdn.example/a.mp4", dest)
    assert not dest.exists()                                                     # keine halbe Datei
    monkeypatch.setattr(vp, "MAX_BYTES", 10_000)
    _client(monkeypatch, lambda req: httpx.Response(200, content=b"<html>nein</html>"))
    with pytest.raises(vp.ProviderError, match="bad_video"):
        vp.download_video("https://cdn.example/a.mp4", dest)
    assert not dest.exists()


def test_allowed_durations_from_model_list(vp, monkeypatch) -> None:
    vp._durations_cache.clear()
    _client(monkeypatch, lambda req: httpx.Response(200, json={"data": [{"id": "m", "supported_durations": [4, 6, 8]}, {"id": "n"}]}))
    assert vp.allowed_durations("m") == [4, 6, 8]
    assert vp.allowed_durations("n") is None
    assert vp.allowed_durations("gibt-es-nicht") is None
    assert vp.nearest(7, [4, 6, 8]) in (6, 8) and vp.nearest(3, [4, 6, 8]) == 4 and vp.nearest(30, [4, 6, 8]) == 8
    assert vp.nearest(7, None) == 7
