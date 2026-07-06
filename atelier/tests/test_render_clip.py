"""Atelier — video.render_clip: await-bare Clip-Erzeugung (submit/poll/download gemockt)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend import video
from conftest import PROJECT_ID


@pytest.mark.asyncio
async def test_render_clip_gibt_rel_zurueck():
    with (
        patch("backend.video.openrouter_key", return_value="sk-or-test"),
        patch("backend.video._source_to_data_url", return_value="data:image/png;base64,xx"),
        patch("backend.video._submit_image_to_video", new=AsyncMock(return_value="remote123")),
        patch("backend.video._poll_until_done", new=AsyncMock(return_value="https://x/vid.mp4")),
        patch("backend.video.download_video", new=AsyncMock(return_value=Path("/tmp/clip99.mp4"))),
    ):
        rel = await video.render_clip(
            PROJECT_ID, source_rel="output/a.png", prompt="a shot",
            model="google/veo-3.1", duration=6, aspect_ratio="16:9",
        )
    assert rel == "videos/clip99.mp4"


@pytest.mark.asyncio
async def test_render_clip_ohne_key_wirft():
    with patch("backend.video.openrouter_key", return_value=""):
        with pytest.raises(RuntimeError):
            await video.render_clip(PROJECT_ID, source_rel="", prompt="p", model="m")


@pytest.mark.asyncio
async def test_render_clip_fehler_propagiert():
    with (
        patch("backend.video.openrouter_key", return_value="sk-or-test"),
        patch("backend.video._source_to_data_url", return_value=None),
        patch("backend.video._submit_image_to_video", new=AsyncMock(side_effect=RuntimeError("submit 400"))),
    ):
        with pytest.raises(RuntimeError, match="submit 400"):
            await video.render_clip(PROJECT_ID, source_rel="", prompt="p", model="m")
