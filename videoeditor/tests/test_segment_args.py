"""ffmpeg-Segment-Argument-Konstruktion — ohne echten ffmpeg-Aufruf."""
from __future__ import annotations

from pathlib import Path

from backend._segment_args import pick_encoder, scale_filter, segment_args
from backend.models import Clip
from backend.render_presets import OutputProfile


def test_scale_filter_variants():
    assert scale_filter("source") is None
    assert scale_filter("720p") == "scale=-2:720"
    assert scale_filter("1280x720") == "scale=1280:720"
    assert scale_filter("") is None


def test_pick_encoder():
    assert pick_encoder(OutputProfile(codec="h264"), None) == "libx264"
    assert pick_encoder(OutputProfile(codec="hevc"), None) == "libx265"
    assert pick_encoder(OutputProfile(codec="source"), "hevc") == "libx265"
    assert pick_encoder(OutputProfile(codec="source"), "h264") == "libx264"
    assert pick_encoder(OutputProfile(codec="source"), None) == "libx264"


def test_copy_segment_uses_stream_copy():
    clip = Clip(id="1", src_start=1.0, src_end=3.0, mode="copy")
    args = segment_args(Path("/src.mp4"), clip, Path("/out.mp4"),
                        reencode=False, profile=OutputProfile(), source_codec=None)
    assert "-c" in args and "copy" in args
    assert "libx264" not in args
    # Seek + Dauer korrekt
    assert "-ss" in args and "1.000" in args
    assert "-t" in args and "2.000" in args


def test_reencode_segment_has_encoder_and_scale():
    clip = Clip(id="1", src_start=0.0, src_end=5.0, mode="reencode")
    profile = OutputProfile(codec="h264", resolution="720p", crf=26)
    args = segment_args(Path("/src.mp4"), clip, Path("/out.mp4"),
                        reencode=True, profile=profile, source_codec="h264")
    assert "libx264" in args
    assert "-vf" in args and "scale=-2:720" in args
    assert "-crf" in args and "26" in args


def test_progress_flag_added_when_requested():
    clip = Clip(id="1", src_start=0.0, src_end=2.0, mode="copy")
    args = segment_args(Path("/src.mp4"), clip, Path("/out.mp4"),
                        reencode=False, profile=OutputProfile(), source_codec=None, progress=True)
    assert "-progress" in args and "pipe:1" in args


def test_no_shell_injection_args_are_list():
    """Alle Argumente sind separate Listenelemente (kein zusammengebauter
    Shell-String) — verhindert Injection über Pfade."""
    clip = Clip(id="1", src_start=0.0, src_end=1.0, mode="copy")
    args = segment_args(Path("/weird; rm -rf/.mp4"), clip, Path("/out.mp4"),
                        reencode=False, profile=OutputProfile(), source_codec=None)
    assert all(isinstance(a, str) for a in args)
    # Der Pfad bleibt EIN Element, wird nicht gesplittet
    assert "/weird; rm -rf/.mp4" in args
