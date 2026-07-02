"""Video-Editor — Wellenform-Peaks aus Audiodateien vorberechnen.

Für die optische Ausrichtung von Audio-Clips an Bild/Schnitt (SPEC-AUDIO.md).
ffmpeg dekodiert die Datei zu mono ``s16le``-PCM auf stdout; daraus werden
Min/Max-Amplituden je Zeit-Bucket berechnet und als normalisierte Floats
(0.0..1.0) zurückgegeben — kompaktes JSON, das das Frontend direkt zeichnet.

Aufruf über ``asyncio.create_subprocess_exec`` mit Args-Liste (keine Shell).
"""
from __future__ import annotations

import asyncio
import struct
from pathlib import Path

from ._ffmpeg import FFmpegError

# Zeitauflösung der Wellenform. 60 Buckets/s reichen fürs Ausrichten und halten
# das JSON klein (~60 Float-Paare pro Sekunde Audio).
PEAKS_PER_SECOND = 60
_PCM_SAMPLE_RATE = 8000  # Downsample beim Dekodieren spart Bandbreite/CPU
_INT16_MAX = 32768.0


async def compute_peaks(media: Path, *, duration: float) -> dict:
    """Dekodiert ``media`` zu mono s16le-PCM und bildet Min/Max-Peaks je Bucket.

    Returns ``{"peaks_per_second": int, "duration": float, "min": [...],
    "max": [...]}`` mit normalisierten Floats in [-1, 1] (min) bzw. [0, 1] (max).
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-v", "error", "-i", str(media),
        "-ac", "1", "-ar", str(_PCM_SAMPLE_RATE),
        "-f", "s16le", "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    pcm, err = await proc.communicate()
    if proc.returncode != 0:
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])

    return peaks_from_pcm(pcm, duration=duration)


def peaks_from_pcm(pcm: bytes, *, duration: float) -> dict:
    """Reine Rechenfunktion (ohne ffmpeg) — separat testbar.

    ``pcm`` ist mono little-endian int16. Buckets werden aus der Sample-Zahl
    und der gewünschten Auflösung gebildet; die Länge wird an ``duration``
    ausgerichtet, damit Zeit→Bucket linear stimmt.
    """
    sample_count = len(pcm) // 2
    if sample_count == 0 or duration <= 0:
        return {"peaks_per_second": PEAKS_PER_SECOND, "duration": max(duration, 0.0),
                "min": [], "max": []}

    samples = struct.unpack(f"<{sample_count}h", pcm[: sample_count * 2])
    bucket_count = max(1, int(round(duration * PEAKS_PER_SECOND)))
    per_bucket = max(1, sample_count // bucket_count)

    mins: list[float] = []
    maxs: list[float] = []
    for b in range(bucket_count):
        start = b * per_bucket
        if start >= sample_count:
            mins.append(0.0)
            maxs.append(0.0)
            continue
        chunk = samples[start : start + per_bucket]
        lo = min(chunk)
        hi = max(chunk)
        mins.append(round(lo / _INT16_MAX, 4))
        maxs.append(round(hi / _INT16_MAX, 4))

    return {
        "peaks_per_second": PEAKS_PER_SECOND,
        "duration": duration,
        "min": mins,
        "max": maxs,
    }
