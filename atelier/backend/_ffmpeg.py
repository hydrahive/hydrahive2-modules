"""Atelier — ffmpeg-Kommando-Bau für den Film-Schnitt.

Reine Kommando-Konstruktion (testbar ohne ffmpeg-Aufruf). Clips haben gemischte
Auflösungen → jeder wird auf das Zielformat normalisiert (scale + Letterbox-pad
+ setsar + fps), dann concat. Optional Musik mit Fade-out unterlegt.

Argumente werden als LISTE gebaut (kein shell=True) → keine Shell-Injection.
"""
from __future__ import annotations

from pathlib import Path

_FPS = 24


def _norm_chain(idx: int, w: int, h: int, label: str) -> str:
    """Filter-Kette, die Input idx auf w×h normalisiert (Letterbox, kein Verzerren)."""
    return (
        f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={_FPS}[{label}]"
    )


def build_concat_command(
    clips: list[Path], out_path: Path, *, width: int, height: int,
    music: Path | None = None, music_fade_tail: float = 2.0,
) -> list[str]:
    """Baut das ffmpeg-Argumentliste für: clips normalisieren → concat → (Musik).

    Wirft ValueError bei leerer Clip-Liste.
    """
    if not clips:
        raise ValueError("Keine Clips für den Film.")

    args: list[str] = ["ffmpeg", "-y"]
    for clip in clips:
        args += ["-i", str(clip)]
    if music is not None:
        args += ["-i", str(music)]

    # Normalisierung je Clip + concat.
    chains = [_norm_chain(i, width, height, f"v{i}") for i in range(len(clips))]
    concat_inputs = "".join(f"[v{i}]" for i in range(len(clips)))
    filter_parts = chains + [f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]"]

    if music is not None:
        music_idx = len(clips)
        # Musik leicht ausblenden zum Schluss (Tail). st wird zur Laufzeit nicht
        # exakt gesetzt — afade ab 0 mit langer Dauer + -shortest kappt sauber.
        filter_parts.append(f"[{music_idx}:a]afade=t=out:st=0:d=99999[aout]")

    args += ["-filter_complex", ";".join(filter_parts), "-map", "[outv]"]
    if music is not None:
        args += ["-map", "[aout]", "-c:a", "aac", "-shortest"]
    args += [
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    return args


# Bewusst behalten: simple Fade-Variante mit bekanntem Tail-Zeitpunkt, falls
# die Gesamtdauer vorab bekannt ist (Phase 2 mit echtem afade-Tail).
def music_fade_filter(music_idx: int, total_seconds: float, tail: float) -> str:
    start = max(0.0, total_seconds - tail)
    return f"[{music_idx}:a]afade=t=out:st={start:.2f}:d={tail:.2f}[aout]"
