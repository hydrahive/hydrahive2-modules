"""Ansage: Text → (Kern-Piper) WAV → 8 kHz G.711, mit Zwischenspeicher und Ersatzton."""
from __future__ import annotations

import io
import struct
import wave

import pytest


def _wav(seconds: float = 1.0, rate: int = 22050, value: int = 1000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        w.writeframes(struct.pack(f"<{n}h", *([value] * n)))
    return buf.getvalue()


@pytest.fixture
def piper(monkeypatch):
    calls = []

    async def fake(text: str, voice: str = ""):
        calls.append(text)
        return _wav(), "audio/wav"
    from backend.media import greeting

    monkeypatch.setattr(greeting, "_synthesize", fake)
    greeting.clear_cache()
    return calls


def test_ansage_wird_g711_mit_8khz(piper) -> None:
    from backend.media import g711, greeting

    audio = greeting.render("Hallo, hier ist HydraHive.", "PCMA")
    assert len(audio) == 8000 + greeting.LEAD_IN_FRAMES * 160          # 1 s + kurze Stille vorneweg
    assert audio[:160] == bytes([g711.SILENCE["PCMA"]]) * 160
    assert set(audio[greeting.LEAD_IN_FRAMES * 160:]) == set(g711.encode(struct.pack("<h", 1000), "PCMA"))
    assert piper == ["Hallo, hier ist HydraHive."]


def test_zwischenspeicher_je_text_aber_codec_getrennt(piper) -> None:
    from backend.media import greeting

    a1 = greeting.render("Hallo", "PCMA")
    a2 = greeting.render("Hallo", "PCMA")
    u = greeting.render("Hallo", "PCMU")
    assert a1 == a2 and a1 != u and piper == ["Hallo"]
    greeting.render("Anderer Text", "PCMA")
    assert piper == ["Hallo", "Anderer Text"]


def test_ersatzton_wenn_piper_nicht_geht(monkeypatch) -> None:
    from backend.media import greeting

    async def broken(text: str, voice: str = ""):
        raise RuntimeError("Piper nicht erreichbar")
    monkeypatch.setattr(greeting, "_synthesize", broken)
    greeting.clear_cache()
    audio = greeting.render("Hallo", "PCMU")
    assert greeting.LAST_SOURCE["Hallo"] == "tone"
    assert 8000 <= len(audio) <= 8000 * 4 and len(set(audio)) > 2, "hörbarer Ton, keine Stille"


def test_kaputtes_wav_ergibt_ersatzton(monkeypatch) -> None:
    from backend.media import greeting

    async def junk(text: str, voice: str = ""):
        return b"kein wav", "audio/wav"
    monkeypatch.setattr(greeting, "_synthesize", junk)
    greeting.clear_cache()
    greeting.render("X", "PCMA")
    assert greeting.LAST_SOURCE["X"] == "tone"


def test_hoechstlaenge_ansage(monkeypatch) -> None:
    from backend.media import greeting

    async def long(text: str, voice: str = ""):
        return _wav(seconds=90, rate=8000), "audio/wav"
    monkeypatch.setattr(greeting, "_synthesize", long)
    greeting.clear_cache()
    assert len(greeting.render("lang", "PCMA")) <= greeting.MAX_SECONDS * 8000 + greeting.LEAD_IN_FRAMES * 160


def test_render_aus_laufender_eventloop(piper) -> None:
    """Der Anruf läuft in einem Thread; render() darf auch aus einem Thread mit eigener Loop aufgerufen werden."""
    import asyncio

    from backend.media import greeting

    async def inside():
        return await asyncio.to_thread(greeting.render, "Thread", "PCMA")
    assert asyncio.run(inside())
