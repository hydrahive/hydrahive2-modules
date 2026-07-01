"""EDL-Sanitizing + Keyframe-Mode-Resolution (der fachliche Kern des Hybrid-Exports).

Läuft ohne echten ffmpeg-Aufruf — reine Logik-Tests.
"""
from __future__ import annotations

from backend.export_service import resolve_modes
from backend.models import EDL, Clip


def test_edl_sanitize_drops_invalid_clips():
    edl = EDL(file_id="abc", timeline=[
        Clip(id="1", src_start=5, src_end=3, mode="copy"),   # invertiert -> raus
        Clip(id="2", src_start=2, src_end=2, mode="copy"),   # leer -> raus
        Clip(id="3", src_start=10, src_end=20, mode="copy"),
        Clip(id="4", src_start=0, src_end=5, mode="reencode"),
    ])
    clean = edl.sanitized()
    assert [c.id for c in clean.timeline] == ["4", "3"]  # nach src_start sortiert


def test_resolve_modes_keeps_copy_on_keyframe():
    clips = [Clip(id="1", src_start=10.0, src_end=15.0, mode="copy")]
    keyframes = [0.0, 5.0, 10.0, 15.0]
    resolved = resolve_modes(clips, keyframes)
    assert resolved[0].mode == "copy"


def test_resolve_modes_downgrades_off_keyframe_copy_to_reencode():
    """Sicherheitsnetz: 'copy' ohne Keyframe würde beim echten Export den
    Clip-Anfang unbemerkt verschieben — muss auf reencode fallen."""
    clips = [Clip(id="1", src_start=10.37, src_end=15.0, mode="copy")]
    keyframes = [0.0, 5.0, 10.0, 15.0]  # kein Keyframe bei 10.37
    resolved = resolve_modes(clips, keyframes)
    assert resolved[0].mode == "reencode"


def test_resolve_modes_tolerates_sub_frame_rounding():
    """Innerhalb der Frame-Toleranz (~1/24s) bleibt copy erlaubt."""
    clips = [Clip(id="1", src_start=10.02, src_end=15.0, mode="copy")]
    keyframes = [10.0]
    resolved = resolve_modes(clips, keyframes)
    assert resolved[0].mode == "copy"


def test_resolve_modes_leaves_explicit_reencode_untouched():
    clips = [Clip(id="1", src_start=10.0, src_end=15.0, mode="reencode")]
    resolved = resolve_modes(clips, keyframes=[10.0])
    assert resolved[0].mode == "reencode"


def test_clip_rejects_invalid_mode():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Clip(id="1", src_start=0, src_end=1, mode="delete-everything")
