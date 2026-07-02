"""End-to-End-Verifikation des Audio-Mix mit echtem ffmpeg.

Baut ein Test-Video (Farbbalken + 440Hz-Ton) und zwei kurze Audiodateien,
exportiert mit einem Mehrspur-EDL (Fades, Gain, O-Ton-Gain) und prüft, dass die
Ausgabe eine Audiospur mit plausibler Dauer hat. Übersprungen, wenn ffmpeg fehlt.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from backend.export_service import render_export
from backend.models import EDL, AudioClip, AudioTrack, Clip, OriginalAudio

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe nicht verfügbar",
)


def _make_video(path: Path, seconds: int = 6) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=25:duration={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path),
    ], check=True)


def _make_tone(path: Path, freq: int, seconds: int) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}",
        "-c:a", "libmp3lame", str(path),
    ], check=True)


def _probe_audio(path: Path) -> dict:
    out = subprocess.run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    return {
        "has_audio": audio is not None,
        "duration": float(data["format"]["duration"]),
    }


def test_multitrack_export_has_audio():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        video = tmp / "in.mp4"
        music = tmp / "music.mp3"
        voice = tmp / "voice.mp3"
        _make_video(video, 6)
        _make_tone(music, 440, 6)
        _make_tone(voice, 880, 3)

        # Video-Schnitt: 0..4s. Zwei Audiospuren mit Gain/Fades + O-Ton leiser.
        edl = EDL(
            file_id="f",
            timeline=[Clip(id="v", src_start=0.0, src_end=4.0, mode="reencode")],
            original_audio=OriginalAudio(gain_db=-6.0),
            audio=[
                AudioTrack(id="music", gain_db=-3.0, clips=[
                    AudioClip(id="m", source_rel="music.mp3", t_start=0.0,
                              src_start=0.0, src_end=4.0, fade_in=0.5, fade_out=0.5),
                ]),
                AudioTrack(id="voice", clips=[
                    AudioClip(id="vo", source_rel="voice.mp3", t_start=1.0,
                              src_start=0.0, src_end=2.0, gain_db=2.0),
                ]),
            ],
        )
        dst = tmp / "out.mp4"

        def resolve(rel: str) -> Path:
            return tmp / rel

        asyncio.run(render_export(
            video, edl.timeline, dst, keyframes=[0.0],
            edl=edl, resolve_audio=resolve,
        ))

        assert dst.is_file()
        info = _probe_audio(dst)
        assert info["has_audio"] is True
        # Video ist 4s geschnitten -> Ausgabe ~4s (Toleranz für Encoder-Padding)
        assert 3.5 <= info["duration"] <= 4.8


def test_overlapping_clips_crossfade_render():
    """Zwei überlappende Clips einer Spur müssen valide rendern (Crossfade)."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        video = tmp / "in.mp4"
        a = tmp / "a.mp3"
        b = tmp / "b.mp3"
        _make_video(video, 8)
        _make_tone(a, 440, 5)
        _make_tone(b, 660, 5)

        edl = EDL(
            file_id="f",
            timeline=[Clip(id="v", src_start=0.0, src_end=6.0, mode="reencode")],
            audio=[AudioTrack(id="t", clips=[
                AudioClip(id="a", source_rel="a.mp3", t_start=0.0, src_start=0.0, src_end=4.0),
                AudioClip(id="b", source_rel="b.mp3", t_start=3.0, src_start=0.0, src_end=4.0),
            ])],
        )
        dst = tmp / "out.mp4"
        asyncio.run(render_export(
            video, edl.timeline, dst, keyframes=[0.0],
            edl=edl, resolve_audio=lambda r: tmp / r,
        ))
        assert dst.is_file()
        assert _probe_audio(dst)["has_audio"] is True


def test_export_without_audio_still_works():
    """Rückwärtskompat: EDL ohne Audio-Mix nimmt den Passthrough-Pfad."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        video = tmp / "in.mp4"
        _make_video(video, 5)
        edl = EDL(file_id="f", timeline=[Clip(id="v", src_start=0.0, src_end=3.0, mode="reencode")])
        dst = tmp / "out.mp4"

        asyncio.run(render_export(
            video, edl.timeline, dst, keyframes=[0.0],
            edl=edl, resolve_audio=lambda r: tmp / r,
        ))
        assert dst.is_file()
        assert _probe_audio(dst)["has_audio"] is True  # O-Ton bleibt erhalten
