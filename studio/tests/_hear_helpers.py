"""Hilfen der 6b-Tests: Anbieter fürs Heraushören ersetzen (Abschnitte mit Zeit), Auftrag abwarten."""
from __future__ import annotations

import time

import pytest
from _subtitle_helpers import P, S


class FakeHear:
    """Statt OpenRouter: nimmt (Datei, Sprache, Modell) entgegen, liefert Abschnitte wie verbose_json."""

    def __init__(self, segments: list[dict] | None = None, error: str | None = None):
        self.calls: list[dict] = []
        self.segments = segments if segments is not None else [
            {"start": 0.3, "end": 1.6, "text": " Da ist er endlich.", "no_speech_prob": 0.01},
            {"start": 1.9, "end": 3.4, "text": " Der alte Ole kommt nach Hause.", "no_speech_prob": 0.02}]
        self.error = error

    def __call__(self, path, language: str, model: str) -> list[dict]:
        self.calls.append({"path": str(path), "language": language, "model": model, "size": path.stat().st_size,
                           "suffix": path.suffix})
        if self.error:
            from backend.hear_provider import ProviderError
            raise ProviderError(self.error)
        return self.segments


@pytest.fixture
def hear(monkeypatch):
    fake = FakeHear()
    monkeypatch.setattr("backend.hear_provider.transcribe", fake)
    monkeypatch.setattr("backend.hear_provider.server_model", lambda: "openai/whisper-large-v3")
    return fake


def wait_hear(client, h, lang: str = "de", timeout: float = 30.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["kind"] == "transcribe"]
        if jobs and jobs[0]["status"] in ("done", "failed", "cancelled"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Heraushören nicht fertig geworden")


H = f"{S}/de/from-audio"
