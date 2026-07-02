"""Wellenform-Peaks-Berechnung (SPEC-AUDIO.md Schritt 2), reine Logik.

Testet peaks_from_pcm ohne echten ffmpeg-Aufruf: die Funktion bekommt rohes
mono s16le-PCM und muss daraus normalisierte Min/Max-Buckets bilden.
"""
from __future__ import annotations

import struct

from backend._audio_peaks import PEAKS_PER_SECOND, peaks_from_pcm


def _pcm(*samples: int) -> bytes:
    return struct.pack(f"<{len(samples)}h", *samples)


def test_empty_pcm_yields_empty_peaks():
    out = peaks_from_pcm(b"", duration=0)
    assert out["min"] == [] and out["max"] == []
    assert out["peaks_per_second"] == PEAKS_PER_SECOND


def test_zero_duration_yields_empty():
    out = peaks_from_pcm(_pcm(1000, -1000), duration=0)
    assert out["min"] == [] and out["max"] == []


def test_bucket_count_scales_with_duration():
    # 2 Sekunden -> 2 * PEAKS_PER_SECOND Buckets
    samples = _pcm(*([10000] * (PEAKS_PER_SECOND * 2 * 4)))
    out = peaks_from_pcm(samples, duration=2.0)
    assert len(out["max"]) == PEAKS_PER_SECOND * 2
    assert len(out["min"]) == PEAKS_PER_SECOND * 2


def test_peaks_are_normalized_to_unit_range():
    # Vollausschlag int16 (+/-32767) -> ~ +/-1.0 normalisiert
    out = peaks_from_pcm(_pcm(32767, -32768, 0, 100), duration=1.0)
    assert max(out["max"]) <= 1.0
    assert min(out["min"]) >= -1.0
    # Der laute Ausschlag muss sichtbar sein
    assert max(out["max"]) > 0.9
    assert min(out["min"]) < -0.9


def test_silence_is_flat_zero():
    out = peaks_from_pcm(_pcm(*([0] * 1000)), duration=1.0)
    assert all(v == 0.0 for v in out["max"])
    assert all(v == 0.0 for v in out["min"])


def test_duration_preserved_in_output():
    out = peaks_from_pcm(_pcm(1, 2, 3, 4), duration=3.5)
    assert out["duration"] == 3.5
