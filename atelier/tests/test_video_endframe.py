"""Atelier — Start-/Endbild (first_frame + last_frame) für Video."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend import video
from conftest import PROJECT_ID


@pytest.mark.asyncio
async def test_submit_sends_first_and_last_frame():
    captured: dict = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"id": "remote-1"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured["payload"] = json
            return FakeResp()

    with patch("backend.video.httpx.AsyncClient", FakeClient):
        await video._submit_image_to_video(
            prompt="p", model="google/veo-3.1", key="k", duration=6,
            aspect_ratio="16:9",
            image_url="data:image/png;base64,START",
            end_image_url="data:image/png;base64,END",
        )

    frames = captured["payload"]["frame_images"]
    assert [f["frame_type"] for f in frames] == ["first_frame", "last_frame"]
    assert frames[0]["image_url"]["url"] == "data:image/png;base64,START"
    assert frames[1]["image_url"]["url"] == "data:image/png;base64,END"


@pytest.mark.asyncio
async def test_submit_without_end_image_only_first_frame():
    captured: dict = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"id": "remote-1"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured["payload"] = json
            return FakeResp()

    with patch("backend.video.httpx.AsyncClient", FakeClient):
        await video._submit_image_to_video(
            prompt="p", model="minimax/hailuo-2.3", key="k", duration=6,
            aspect_ratio="16:9",
            image_url="data:image/png;base64,START",
            end_image_url=None,
        )

    frames = captured["payload"]["frame_images"]
    assert [f["frame_type"] for f in frames] == ["first_frame"]


@pytest.mark.asyncio
async def test_render_clip_passes_end_image():
    seen: dict = {}

    async def fake_submit(**kwargs):
        seen.update(kwargs)
        return "remote123"

    def fake_data_url(_pid, rel):
        return f"data:image/png;base64,{rel}" if rel else None

    with (
        patch("backend.video.openrouter_key", return_value="sk-or-test"),
        patch("backend.video._source_to_data_url", side_effect=fake_data_url),
        patch("backend.video._submit_image_to_video", new=AsyncMock(side_effect=fake_submit)),
        patch("backend.video._poll_until_done", new=AsyncMock(return_value="https://x/vid.mp4")),
        patch("backend.video.download_video", new=AsyncMock(return_value=Path("/tmp/clip.mp4"))),
    ):
        rel = await video.render_clip(
            PROJECT_ID, source_rel="images/a.png", prompt="a shot",
            model="google/veo-3.1", duration=6, aspect_ratio="16:9",
            end_source_rel="images/z.png",
        )

    assert rel == "videos/clip.mp4"
    assert seen["image_url"] == "data:image/png;base64,images/a.png"
    assert seen["end_image_url"] == "data:image/png;base64,images/z.png"


def test_start_video_job_stores_end_source_rel():
    def _swallow(coro, *_a, **_k):
        coro.close()  # verhindert "coroutine was never awaited"-Warnung
        return None

    with patch("backend.video.asyncio.create_task", _swallow):
        job = video.start_video_job(PROJECT_ID, {
            "source_rel": "images/a.png",
            "end_source_rel": "images/z.png",
            "prompt": "p",
            "model": "google/veo-3.1",
            "duration": 6,
        })
    assert job["end_source_rel"] == "images/z.png"
