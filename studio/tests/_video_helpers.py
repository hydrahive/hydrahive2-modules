"""Ersatz für den Video-Anbieter in den 3b-Tests (submit → wait → download), mit Zähler für gleichzeitige Videos."""
from __future__ import annotations

import threading
import time

import pytest

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\0" * 64


class FakeVideo:
    """Ersatz für den Video-Anbieter: submit → wait → download."""

    def __init__(self, *, fail_at: str | None = None, code: str = "provider_rejected", delay: float = 0.0, durations=None):
        self.calls: list[tuple[str, dict]] = []
        self.fail_at, self.code, self.delay, self.durations = fail_at, code, delay, durations
        self.active = self.peak = 0
        self.lock = threading.Lock()

    def _maybe_fail(self, step: str) -> None:
        if self.fail_at == step:
            from backend.video_provider import ProviderError
            raise ProviderError(self.code)

    def submit(self, **kw):
        self.calls.append(("submit", kw))
        self._maybe_fail("submit")
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        return "remote-1"

    def wait(self, remote_id, *, duration):
        self.calls.append(("wait", {"remote_id": remote_id, "duration": duration}))
        try:
            if self.delay:
                time.sleep(self.delay)
            self._maybe_fail("wait")
            return "https://cdn.example/v.mp4"
        finally:
            with self.lock:
                self.active -= 1

    def download(self, url, dest):
        self.calls.append(("download", {"url": url}))
        self._maybe_fail("download")
        dest.write_bytes(MP4)

    def allowed(self, model):
        return self.durations


@pytest.fixture
def video(monkeypatch):
    fake = FakeVideo()
    _install(monkeypatch, fake)
    return fake


def _install(monkeypatch, fake: FakeVideo) -> None:
    monkeypatch.setattr("backend.video_provider.submit_video", fake.submit)
    monkeypatch.setattr("backend.video_provider.wait_for_video", fake.wait)
    monkeypatch.setattr("backend.video_provider.download_video", fake.download)
    monkeypatch.setattr("backend.video_provider.allowed_durations", fake.allowed)
