"""Sprache/Stille erkennen je 20-ms-Rahmen (PLAN-AGENT-2B): Satzende, Schweigen, Dazwischenreden."""
from __future__ import annotations

import math
import random
import struct

import pytest

FRAME = 160                                 # 20 ms bei 8 kHz


def _frame(level: int, *, freq: float = 220.0, seed: int = 0) -> bytes:
    """Ein 20-ms-PCM-Rahmen: Sinus (≈ Sprache) mit Amplitude ``level``; level 0 = leises Rauschen."""
    rnd = random.Random(seed)
    if level == 0:
        return struct.pack(f"<{FRAME}h", *(rnd.randint(-30, 30) for _ in range(FRAME)))
    return struct.pack(f"<{FRAME}h", *(int(level * math.sin(2 * math.pi * freq * n / 8000)) for n in range(FRAME)))


def _feed(vad, frames):
    events = []
    for f in frames:
        events.extend(vad.feed(f))
    return events


def _speech(ms: int, level: int = 4000):
    return [_frame(level, seed=i) for i in range(ms // 20)]


def _silence(ms: int):
    return [_frame(0, seed=i) for i in range(ms // 20)]


def test_satz_dann_stille_ergibt_ein_satzende_mit_ganzer_aeusserung() -> None:
    from backend.media.vad import Vad

    v = Vad(end_silence_ms=700)
    events = _feed(v, _silence(400) + _speech(1200) + _silence(800))
    kinds = [e.kind for e in events]
    assert kinds == ["speech_start", "utterance"]
    utt = events[-1].pcm
    assert 1200 * 16 <= len(utt) <= (1200 + 800 + 300) * 16, "Satz + kurzer Vorlauf, ohne die ganze Stille davor"


def test_kurze_pause_im_satz_beendet_ihn_nicht() -> None:
    from backend.media.vad import Vad

    v = Vad(end_silence_ms=700)
    events = _feed(v, _speech(600) + _silence(400) + _speech(600) + _silence(800))
    assert [e.kind for e in events] == ["speech_start", "utterance"]


def test_einzelnes_knacken_ist_keine_sprache() -> None:
    from backend.media.vad import Vad

    v = Vad()
    events = _feed(v, _silence(400) + _speech(40, level=9000) + _silence(1500))
    assert events == []


def test_lautes_rauschen_hebt_die_schwelle() -> None:
    """Brummen knapp über der Grundschwelle (RMS ≈ 420): erst nach dem Lernen ist es keine Sprache mehr."""
    from backend.media.vad import Vad

    v = Vad()
    v.noise = 160.0                                                        # bereits etwas Rauschen gelernt
    hum = [_frame(600, freq=60.0, seed=i) for i in range(200)]             # 4 s, RMS ≈ 424
    assert _feed(v, hum) == [], "Rauschen über 400 wird durch die gelernte Schwelle (3 × Rauschen) geschluckt"


def test_rauschen_auf_der_leitung_wird_gelernt() -> None:
    """Gleichmäßiges Grundrauschen hebt die Schwelle – es wird nicht als Sprache gewertet."""
    from backend.media.vad import Vad

    v = Vad()
    noise = [_frame(300, freq=60.0, seed=i) for i in range(150)]          # 3 s Brummen
    assert _feed(v, noise) == []
    events = _feed(v, _speech(800, level=5000) + noise[:40])
    assert [e.kind for e in events] == ["speech_start", "utterance"]


def test_hoechstlaenge_einer_aeusserung() -> None:
    from backend.media.vad import Vad

    v = Vad(max_utterance_ms=2000)
    events = _feed(v, _speech(3000))
    assert [e.kind for e in events][:2] == ["speech_start", "utterance"]
    assert len(events[1].pcm) <= 2100 * 16


def test_schweigen_meldet_sich_nach_zeit() -> None:
    from backend.media.vad import Vad

    v = Vad(no_input_ms=1000)
    events = _feed(v, _silence(1100))
    assert [e.kind for e in events] == ["no_input"]
    assert _feed(v, _silence(500)) == [], "nur einmal je Abschnitt"
    v.reset()
    assert [e.kind for e in _feed(v, _silence(1100))] == ["no_input"]


def test_dazwischenreden_waehrend_eigener_ansage() -> None:
    """Spricht der Anrufer 300 ms, während HydraHive spricht: Barge-in."""
    from backend.media.vad import Vad

    v = Vad(barge_in_ms=300)
    _feed(v, _silence(500))
    v.speaking = True
    assert "barge_in" not in [e.kind for e in _feed(v, _speech(200))], "200 ms reichen noch nicht"
    assert [e.kind for e in _feed(v, _speech(100))].count("barge_in") == 1, "ab 300 ms genau einmal"
    v2 = Vad(barge_in_ms=300)
    v2.speaking = False
    assert "barge_in" not in [e.kind for e in _feed(v2, _speech(600))], "nur während HydraHive spricht"


def test_echo_der_eigenen_stimme_ist_kein_dazwischenreden() -> None:
    """Leises Echo (deutlich unter Sprachpegel) während HydraHive spricht löst nichts aus."""
    from backend.media.vad import Vad

    v = Vad(barge_in_ms=300)
    _feed(v, _silence(500))
    v.speaking = True
    assert _feed(v, [_frame(250, seed=i) for i in range(40)]) == []


@pytest.mark.parametrize("bad", [b"", b"\x00" * 3, b"\x00" * 100])
def test_falsche_rahmen_werden_ignoriert(bad: bytes) -> None:
    from backend.media.vad import Vad

    assert Vad().feed(bad) == []


def test_pegel() -> None:
    from backend.media.vad import rms

    assert rms(_frame(0)) < 40
    assert 2700 < rms(_frame(4000)) < 3000                                # Sinus: A / √2
