"""Hilfen der 5c-Tests: Sprach-Anbieter ersetzen (echte kleine WAV), Auftrag abwarten."""
from __future__ import annotations

import io
import math
import struct
import time
import wave

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"


def wav(seconds: float = 1.0, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 10))) for i in range(int(seconds * rate))))
    return buf.getvalue()


class FakeVoice:
    """Statt OpenRouter/Piper: nimmt (Text, Stimme, Modell) entgegen, liefert (Daten, Endung, Stimme, Hinweis)."""

    def __init__(self, data: bytes | None = None, error: str | None = None, voices=("af_bella", "af_nicole")):
        self.calls: list[dict] = []
        self.data, self.error, self.voices = data if data is not None else wav(1.5), error, list(voices)

    def __call__(self, text: str, voice: str, model: str):
        self.calls.append({"text": text, "voice": voice, "model": model})
        if self.error:
            from backend.voice_provider import ProviderError
            raise ProviderError(self.error)
        used = voice if voice in self.voices else (self.voices[0] if self.voices else "")
        return self.data, "wav", used, ("Stimme ersetzt" if voice and voice != used else None)


@pytest.fixture
def voice(monkeypatch):
    fake = FakeVoice()
    monkeypatch.setattr("backend.voice_provider.synthesize", fake)
    monkeypatch.setattr("backend.voice_provider.voices", lambda model: list(fake.voices))
    monkeypatch.setattr("backend.voice_provider.server_default_model", lambda: "server/tts")
    return fake


def wait_job(client, h, target: str, timeout: float = 8.0, job_id: str | None = None) -> dict:
    """Auf den jüngsten Auftrag für `target` warten – mit `job_id` genau auf diesen (sonst kann bei schnell
    nacheinander gestarteten Aufträgen der vorige, schon fertige zurückkommen)."""
    end = time.time() + timeout
    while time.time() < end:
        jobs = [j for j in client.get(f"{P}/jobs", headers=h).json()["jobs"] if j["target"] == target and (job_id is None or j["id"] == job_id)]
        if jobs and jobs[0]["status"] in ("done", "failed", "cancelled"):
            return jobs[0]
        time.sleep(0.05)
    raise AssertionError("Auftrag nicht fertig geworden")


def scene_with_shot(client, h, **shot) -> tuple[dict, dict]:
    sc = client.post(f"{P}/scenes", headers=h, json={"title": "Hafen"}).json()
    s = client.post(f"{P}/scenes/{sc['id']}/shots", headers=h, json={"prompt": "Ole am Steg", "duration": 4, **shot}).json()
    return sc, s
