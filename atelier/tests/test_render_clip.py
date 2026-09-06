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
async def test_render_clip_local_nutzt_core_runner():
    output = Path(video.storage.videos_dir(PROJECT_ID)) / "local.mp4"
    output.write_bytes(b"video")
    fake_backend = object()
    with (
        patch("hydrahive.llm._config.load_config", return_value={"media_backends": []}),
        patch("hydrahive.llm.video_backends.resolve_local_workflow", return_value=(fake_backend, {}), create=True),
        patch("hydrahive.llm.video_backends.run_local_media", new=AsyncMock(return_value=output), create=True) as runner,
        patch("backend.video.openrouter_key", side_effect=AssertionError),
    ):
        rel = await video.render_clip(
            PROJECT_ID, source_rel="", prompt="a shot",
            model="local:node/workflow", duration=5,
        )
    runner.assert_awaited_once()
    assert rel == "videos/local.mp4"


@pytest.mark.asyncio
async def test_render_clip_local_reicht_endbild_an_core_runner():
    output = Path(video.storage.videos_dir(PROJECT_ID)) / "local-end.mp4"
    output.write_bytes(b"video")
    fake_backend = object()
    with (
        patch("hydrahive.llm._config.load_config", return_value={"media_backends": []}),
        patch("hydrahive.llm.video_backends.resolve_local_workflow", return_value=(fake_backend, {}), create=True),
        patch("hydrahive.llm.video_backends.run_local_media", new=AsyncMock(return_value=output), create=True) as runner,
        patch("backend.video._source_to_data_url", side_effect=["data:image/png;base64,start", "data:image/png;base64,end"]),
    ):
        await video.render_clip(
            PROJECT_ID, source_rel="images/start.png", end_source_rel="images/end.png",
            prompt="transition", model="local:node/flf2v", duration=5,
        )
    params = runner.await_args.args[3]
    assert params.image_url.endswith("start")
    assert params.end_image_url.endswith("end")


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
