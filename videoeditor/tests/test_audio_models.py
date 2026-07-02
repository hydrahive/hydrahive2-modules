"""Audio-Datenmodell für Nachvertonung (SPEC-AUDIO.md Schritt 1).

Reine Modell-/Logik-Tests, kein ffmpeg. Prüft Validierung, Spur-Sanitizing,
Rückwärtskompatibilität alter EDLs und die has_audio_mix-Entscheidung.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.models import (
    AudioClip,
    AudioTrack,
    Clip,
    EDL,
    OriginalAudio,
)


# ---- AudioClip / AudioTrack Validierung --------------------------------------

def test_audioclip_requires_source_rel():
    with pytest.raises(ValidationError):
        AudioClip(id="c1", source_rel="", src_end=5)


def test_audioclip_defaults():
    c = AudioClip(id="c1", source_rel="generated/x.mp3", src_end=10)
    assert c.t_start == 0.0
    assert c.src_start == 0.0
    assert c.gain_db == 0.0
    assert c.fade_in == 0.0 and c.fade_out == 0.0


def test_audioclip_rejects_negative_fade():
    with pytest.raises(ValidationError):
        AudioClip(id="c1", source_rel="a.wav", src_end=5, fade_in=-1)


def test_audioclip_rejects_zero_src_end():
    with pytest.raises(ValidationError):
        AudioClip(id="c1", source_rel="a.wav", src_end=0)


def test_audiotrack_defaults():
    t = AudioTrack(id="t1")
    assert t.name == "Audio"
    assert t.mute is False and t.solo is False
    assert t.clips == []


# ---- Spur-Sanitizing ----------------------------------------------------------

def test_track_sanitize_drops_invalid_and_sorts_by_t_start():
    t = AudioTrack(id="t1", clips=[
        AudioClip(id="a", source_rel="x.mp3", t_start=10, src_start=0, src_end=5),
        AudioClip(id="b", source_rel="x.mp3", t_start=2, src_start=5, src_end=3),   # invertiert -> raus
        AudioClip(id="c", source_rel="x.mp3", t_start=0, src_start=0, src_end=4),
        AudioClip(id="d", source_rel="x.mp3", t_start=5, src_start=2, src_end=2),   # leer -> raus
    ])
    clean = t.sanitized()
    assert [c.id for c in clean.clips] == ["c", "a"]  # nach t_start sortiert


def test_track_sanitize_preserves_track_flags():
    t = AudioTrack(id="t1", name="Musik", mute=True, solo=True, gain_db=-6.0, clips=[])
    clean = t.sanitized()
    assert clean.name == "Musik"
    assert clean.mute is True and clean.solo is True and clean.gain_db == -6.0


# ---- EDL Rückwärtskompatibilität ---------------------------------------------

def test_edl_without_audio_fields_is_valid():
    """Altes EDL-JSON (nur file_id + timeline) muss weiterhin parsen."""
    edl = EDL.model_validate({
        "file_id": "abc",
        "timeline": [{"id": "1", "src_start": 0, "src_end": 5, "mode": "copy"}],
    })
    assert edl.audio == []
    assert edl.original_audio.mute is False
    assert edl.original_audio.gain_db == 0.0


def test_edl_sanitize_cleans_video_and_audio():
    edl = EDL(
        file_id="abc",
        timeline=[
            Clip(id="v2", src_start=10, src_end=20, mode="copy"),
            Clip(id="v1", src_start=0, src_end=5, mode="reencode"),
        ],
        audio=[AudioTrack(id="t1", clips=[
            AudioClip(id="a", source_rel="x.mp3", t_start=5, src_start=3, src_end=3),  # leer
            AudioClip(id="b", source_rel="x.mp3", t_start=0, src_start=0, src_end=4),
        ])],
    )
    clean = edl.sanitized()
    assert [c.id for c in clean.timeline] == ["v1", "v2"]
    assert [c.id for c in clean.audio[0].clips] == ["b"]


def test_edl_sanitize_keeps_empty_tracks():
    """Leere Spuren bleiben — sonst verliert die UI die Spur-Struktur."""
    edl = EDL(file_id="abc", audio=[AudioTrack(id="empty", clips=[])])
    clean = edl.sanitized()
    assert len(clean.audio) == 1
    assert clean.audio[0].id == "empty"


# ---- has_audio_mix-Entscheidung ----------------------------------------------

def test_has_audio_mix_false_for_plain_edl():
    edl = EDL(file_id="abc", timeline=[Clip(id="1", src_start=0, src_end=5)])
    assert edl.has_audio_mix() is False


def test_has_audio_mix_true_with_audio_clip():
    edl = EDL(file_id="abc", audio=[AudioTrack(id="t1", clips=[
        AudioClip(id="a", source_rel="x.mp3", src_end=5),
    ])])
    assert edl.has_audio_mix() is True


def test_has_audio_mix_true_when_original_muted():
    edl = EDL(file_id="abc", original_audio=OriginalAudio(mute=True))
    assert edl.has_audio_mix() is True


def test_has_audio_mix_true_when_original_gain_changed():
    edl = EDL(file_id="abc", original_audio=OriginalAudio(gain_db=-3.0))
    assert edl.has_audio_mix() is True


def test_has_audio_mix_false_for_empty_track_only():
    edl = EDL(file_id="abc", audio=[AudioTrack(id="t1", clips=[])])
    assert edl.has_audio_mix() is False
