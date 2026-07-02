"""Video-Editor — ffmpeg-Argument-Bau für Export-Segmente.

Reine Kommando-Konstruktion (testbar ohne ffmpeg-Aufruf), ausgelagert aus
export_service.py. Args immer als Liste — keine Shell-Injection.
"""
from __future__ import annotations

import re
from pathlib import Path

from .models import Clip
from .render_presets import OutputProfile


def scale_filter(resolution: str) -> str | None:
    """'720p' → scale=-2:720, '1280x720' → scale=1280:720, 'source' → None."""
    if not resolution or resolution == "source":
        return None
    m = re.fullmatch(r"(\d+)p", resolution)
    if m:
        return f"scale=-2:{int(m.group(1))}"
    m = re.fullmatch(r"(\d+)x(\d+)", resolution)
    if m:
        return f"scale={m.group(1)}:{m.group(2)}"
    return None


def pick_encoder(profile: OutputProfile, source_codec: str | None) -> str:
    """libx264 für h264, libx265 für hevc; 'source' folgt dem Quell-Codec."""
    codec = (profile.codec or "source").lower()
    if codec == "source":
        c = (source_codec or "").lower()
        codec = "hevc" if c in ("hevc", "h265") else "h264"
    return "libx265" if codec == "hevc" else "libx264"


def quality_args(profile: OutputProfile) -> list[str]:
    if profile.bitrate:
        return ["-b:v", profile.bitrate]
    if profile.crf is not None:
        return ["-crf", str(profile.crf)]
    return ["-crf", "20"]  # sinnvoller Default


def segment_args(
    src: Path, clip: Clip, out: Path, *, reencode: bool,
    profile: OutputProfile, source_codec: str | None, progress: bool = False,
) -> list[str]:
    """Baut die ffmpeg-Argumentliste für genau ein Segment."""
    dur = clip.src_end - clip.src_start
    base = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    seek_in = ["-ss", f"{clip.src_start:.3f}", "-i", str(src), "-t", f"{dur:.3f}"]
    prog = ["-progress", "pipe:1", "-nostats"] if progress else []

    if not reencode:
        return base + seek_in + ["-c", "copy", "-avoid_negative_ts", "make_zero", *prog, str(out)]

    encoder = pick_encoder(profile, source_codec)
    args = base + seek_in + ["-c:v", encoder, "-preset", "medium", *quality_args(profile)]
    vf = scale_filter(profile.resolution)
    if vf:
        args += ["-vf", vf]
    args += ["-pix_fmt", "yuv420p"]
    if profile.audio_codec == "copy":
        args += ["-c:a", "copy"]
    else:
        args += ["-c:a", profile.audio_codec, "-b:a", profile.audio_bitrate]
    args += [*prog, str(out)]
    return args
