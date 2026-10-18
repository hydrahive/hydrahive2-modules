"""Hilfen der 5c-2-Tests: Musik-Anbieter ersetzen (echte kleine WAV statt MP3 – ffprobe prüft nur „ist Ton“)."""
from __future__ import annotations

import pytest
from _voice_helpers import wav


class FakeMusic:
    def __init__(self, data: bytes | None = None, error: str | None = None):
        self.calls: list[dict] = []
        self.data, self.error = data if data is not None else wav(3.0), error

    def __call__(self, prompt: str, model: str) -> bytes:
        self.calls.append({"prompt": prompt, "model": model})
        if self.error:
            from backend.music_provider import ProviderError
            raise ProviderError(self.error)
        return self.data


@pytest.fixture
def music(monkeypatch):
    fake = FakeMusic()
    monkeypatch.setattr("backend.music_provider.generate", fake)
    monkeypatch.setattr("backend.music_provider.server_default_model", lambda: "server/lyria")
    return fake
