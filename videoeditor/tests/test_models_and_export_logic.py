"""EDL-Sanitizing + Keyframe-Mode-Entscheidung + Output-Profil-Logik.

Läuft ohne echten ffmpeg-Aufruf — reine Logik-Tests.
"""
from __future__ import annotations

from backend.export_service import _needs_reencode
from backend.models import EDL, Clip
from backend.render_presets import OutputProfile, get_preset, output_forces_reencode


def test_edl_sanitize_drops_invalid_clips():
    edl = EDL(file_id="abc", timeline=[
        Clip(id="1", src_start=5, src_end=3, mode="copy"),   # invertiert -> raus
        Clip(id="2", src_start=2, src_end=2, mode="copy"),   # leer -> raus
        Clip(id="3", src_start=10, src_end=20, mode="copy"),
        Clip(id="4", src_start=0, src_end=5, mode="reencode"),
    ])
    clean = edl.sanitized()
    assert [c.id for c in clean.timeline] == ["4", "3"]  # nach src_start sortiert


# ---- Clip-Ebene: _needs_reencode ---------------------------------------------

def test_copy_on_keyframe_stays_copy():
    clip = Clip(id="1", src_start=10.0, src_end=15.0, mode="copy")
    assert _needs_reencode(clip, [0.0, 5.0, 10.0, 15.0], profile_forces=False) is False


def test_copy_off_keyframe_forces_reencode():
    """'copy' ohne Keyframe würde den Clip-Anfang unbemerkt verschieben."""
    clip = Clip(id="1", src_start=10.37, src_end=15.0, mode="copy")
    assert _needs_reencode(clip, [0.0, 5.0, 10.0, 15.0], profile_forces=False) is True


def test_copy_within_frame_tolerance_stays_copy():
    clip = Clip(id="1", src_start=10.02, src_end=15.0, mode="copy")
    assert _needs_reencode(clip, [10.0], profile_forces=False) is False


def test_explicit_reencode_untouched():
    clip = Clip(id="1", src_start=10.0, src_end=15.0, mode="reencode")
    assert _needs_reencode(clip, [10.0], profile_forces=False) is True


def test_profile_forces_overrides_copy():
    """Erzwingt das Profil Re-Encode (Skalierung etc.), muss auch ein
    keyframe-genauer copy-Clip transkodieren (homogene concat-Streams)."""
    clip = Clip(id="1", src_start=10.0, src_end=15.0, mode="copy")
    assert _needs_reencode(clip, [10.0], profile_forces=True) is True


def test_clip_rejects_invalid_mode():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Clip(id="1", src_start=0, src_end=1, mode="delete-everything")


# ---- Profil-Ebene: output_forces_reencode ------------------------------------

def test_passthrough_does_not_force_reencode():
    profile = OutputProfile(codec="source", resolution="source", audio_codec="copy")
    forced, _ = output_forces_reencode(profile, {"video_codec": "h264"})
    assert forced is False


def test_resolution_change_forces_reencode():
    profile = OutputProfile(codec="h264", resolution="720p")
    forced, reason = output_forces_reencode(profile, {"video_codec": "h264"})
    assert forced is True
    assert "720p" in reason


def test_crf_forces_reencode():
    profile = OutputProfile(codec="source", resolution="source", crf=20)
    forced, _ = output_forces_reencode(profile, None)
    assert forced is True


def test_codec_change_forces_reencode():
    profile = OutputProfile(codec="hevc", resolution="source")
    forced, reason = output_forces_reencode(profile, {"video_codec": "h264"})
    assert forced is True
    assert "hevc" in reason


def test_passthrough_preset_exists_and_is_copy():
    p = get_preset("passthrough")
    assert p is not None
    assert p.profile.codec == "source"
    assert p.profile.resolution == "source"


def test_unknown_preset_returns_none():
    assert get_preset("does-not-exist") is None
