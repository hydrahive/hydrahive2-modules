"""Ansagetext → G.711-Ton für das Telefon (PLAN-ANRUFE-2A, Schritt 4).

Sprache kommt vom lokalen Piper des Kerns (hydrahive.voice.tts.synthesize_local, kein Cloud-Dienst). Ergebnis je
(Text, Codec) zwischengespeichert, damit der Anrufer nicht wartet. Geht Piper nicht, kommt ein kurzer Hinweiston –
der Anrufer hört dann wenigstens, dass abgenommen wurde. Höchstlänge begrenzt.
"""
from __future__ import annotations

import asyncio
import io
import logging
import math
import struct
import threading
import wave

from . import g711

logger = logging.getLogger(__name__)
MAX_SECONDS = 30
LEAD_IN_FRAMES = 10                     # 200 ms Stille vorneweg: Sprachweg „aufmachen“, erste Silbe nicht verschluckt
_CACHE: dict[tuple[str, str], bytes] = {}
_PCM: dict[str, bytes] = {}
LAST_SOURCE: dict[str, str] = {}        # Text → "piper" | "tone" (für Anzeige/Tests)
_LOCK = threading.Lock()


async def _synthesize(text: str, voice: str = "") -> tuple[bytes, str]:
    from hydrahive.voice.tts import synthesize_local
    return await synthesize_local(text, voice)


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()
        _PCM.clear()
        LAST_SOURCE.clear()


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    box: dict = {}

    def worker():
        try:
            box["v"] = asyncio.run(coro)
        except BaseException as e:  # noqa: BLE001 - an den Aufrufer weitergeben
            box["e"] = e
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join()
    if "e" in box:
        raise box["e"]
    return box["v"]


def _wav_to_pcm8k(wav_bytes: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError("nur 16 Bit")
        pcm = w.readframes(w.getnframes())
        return g711.to_8k_mono(pcm, rate=w.getframerate(), channels=w.getnchannels())


def _tone() -> bytes:
    """Zwei kurze Töne (440 Hz), dazwischen Pause – deutlich als „abgenommen“ erkennbar."""
    beep = [int(8000 * math.sin(2 * math.pi * 440 * n / 8000)) for n in range(2400)]
    pause = [0] * 1600
    samples = beep + pause + beep + pause
    return struct.pack(f"<{len(samples)}h", *samples)


def _pcm_for(text: str) -> bytes:
    """Sprache als 8-kHz-PCM, je Text einmal erzeugt (Piper oder Ersatzton)."""
    with _LOCK:
        if text in _PCM:
            return _PCM[text]
    try:
        wav_bytes, _ = _run(_synthesize(text))
        pcm = _wav_to_pcm8k(wav_bytes)
        if not pcm:
            raise ValueError("leer")
        source = "piper"
    except Exception as e:  # noqa: BLE001 - jede Störung → Ersatzton, der Anruf geht weiter
        logger.warning("telephony: Ansage nicht erzeugbar (%s) – Ersatzton", type(e).__name__)
        pcm, source = _tone(), "tone"
    pcm = pcm[: MAX_SECONDS * 8000 * 2]
    with _LOCK:
        _PCM[text] = pcm
        LAST_SOURCE[text] = source
    return pcm


def render(text: str, codec: str) -> bytes:
    key = (text, codec)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    audio = bytes([g711.SILENCE[codec]]) * (LEAD_IN_FRAMES * 160) + g711.encode(_pcm_for(text), codec)
    with _LOCK:
        _CACHE[key] = audio
    return audio
