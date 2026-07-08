"""Atelier — Regie-Film-Mux: Original-Clip-Ton + zeitversetzte Szenen-Musik.

Reine ffmpeg-Argument-Bauerei (kein echter ffmpeg-Call).
"""
from __future__ import annotations

from pathlib import Path

from backend import _director_mux


def _clips(n: int) -> list[Path]:
    return [Path(f"/tmp/clip{i}.mp4") for i in range(n)]


def test_no_music_uses_original_audio_concat():
    """Ohne Szenen-Musik: reiner Clip-Ton-Concat, kein amix."""
    clips = _clips(2)
    meta = [{"has_audio": True, "duration": 5.0}, {"has_audio": False, "duration": 4.0}]
    args = _director_mux.build_director_mux_command(
        clips, out_path=Path("/tmp/out.mp4"), width=1280, height=720,
        clip_meta=meta, scene_music=[],
    )
    fc = args[args.index("-filter_complex") + 1]
    assert "amix" not in fc
    assert "concat=n=2:v=1:a=1" in fc  # Video + Original-Ton
    # Stille-Quelle für den tonlosen zweiten Clip muss existieren
    assert "anullsrc" in " ".join(args)


def test_scene_music_is_delayed_and_mixed_under_original():
    """Szenen-Musik wird per adelay an die Szenen-Startzeit gesetzt und leiser gemischt."""
    clips = _clips(3)
    meta = [{"has_audio": True, "duration": 5.0}] * 3
    # Szene 2 startet nach Clip 0+1 = 10.0 s
    scene_music = [
        {"music_path": Path("/tmp/m_a.mp3"), "t_start": 0.0},
        {"music_path": Path("/tmp/m_b.mp3"), "t_start": 10.0},
    ]
    args = _director_mux.build_director_mux_command(
        clips, out_path=Path("/tmp/out.mp4"), width=1280, height=720,
        clip_meta=meta, scene_music=scene_music, music_gain=0.35,
    )
    joined = " ".join(args)
    fc = args[args.index("-filter_complex") + 1]

    # Beide Musikdateien als Inputs
    assert "/tmp/m_a.mp3" in joined
    assert "/tmp/m_b.mp3" in joined
    # Verzögerung der zweiten Musik um 10000 ms (adelay in ms)
    assert "adelay=10000|10000" in fc
    # Erste Musik ohne/mit Delay 0
    assert "adelay=0|0" in fc
    # Lautstärke-Absenkung
    assert "volume=0.35" in fc
    # Mix aus Original-Ton + 2 Musikstücken, ohne Normalisierung (Original bleibt laut)
    assert "amix=inputs=3" in fc
    assert "normalize=0" in fc


def test_empty_clips_raises():
    try:
        _director_mux.build_director_mux_command(
            [], out_path=Path("/tmp/out.mp4"), width=1280, height=720,
            clip_meta=[], scene_music=[],
        )
    except ValueError:
        return
    raise AssertionError("erwartet ValueError bei leerer Clip-Liste")
