"""Atelier — ffmpeg-Kommando-Bau für den Film-Schnitt.

Reine Kommando-Konstruktion (testbar ohne ffmpeg-Aufruf). Clips haben gemischte
Auflösungen → jeder wird auf das Zielformat normalisiert (scale + Letterbox-pad
+ setsar + fps), dann concat. Optional Musik mit Fade-out unterlegt.

Argumente werden als LISTE gebaut (kein shell=True) → keine Shell-Injection.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

_FPS = 24


async def probe_clip(video: Path) -> dict:
    """Ermittelt {has_audio, duration} eines Clips via ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type", "-of", "json", str(video),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    import json
    try:
        data = json.loads(out.decode("utf-8", "replace"))
    except (json.JSONDecodeError, ValueError):
        return {"has_audio": False, "duration": 0.0}
    streams = data.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    try:
        duration = float(data.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {"has_audio": has_audio, "duration": duration}


async def extract_last_frame(video: Path, out_jpg: Path) -> None:
    """Extrahiert den letzten Frame eines Videos als JPG (für Fortsetzungen).

    -sseof -0.5: greift 0,5s vor Ende → robust gegen exakte Endzeit. Wirft
    RuntimeError bei ffmpeg-Fehler.
    """
    args = [
        "ffmpeg", "-y", "-sseof", "-0.5", "-i", str(video),
        "-update", "1", "-q:v", "2", str(out_jpg),
    ]
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not out_jpg.is_file():
        tail = (stderr or b"").decode("utf-8", "replace")[-300:]
        raise RuntimeError(f"Frame-Extraktion fehlgeschlagen: {tail}")


def _norm_chain(idx: int, w: int, h: int, label: str) -> str:
    """Filter-Kette, die Input idx auf w×h normalisiert (Letterbox, kein Verzerren)."""
    return (
        f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={_FPS}[{label}]"
    )


def _audio_chain(idx: int, has_audio: bool, duration: float, silence_idx: int, label: str) -> str:
    """Audio-Kette je Clip: echter Ton (auf Clip-Länge aufgefüllt) ODER Stille.

    Beides auf die Clip-Dauer getrimmt — sonst läuft die Stille endlos und der
    Render hängt. Garantiert für JEDEN Clip eine Audiospur, damit concat a=1
    funktioniert (sonst geht der Ton verloren / der Filter bricht).
    """
    dur = max(0.1, duration)
    if has_audio:
        return (
            f"[{idx}:a]aresample=44100,apad,atrim=0:{dur:.3f},"
            f"asetpts=PTS-STARTPTS[{label}]"
        )
    return f"[{silence_idx}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[{label}]"


def build_concat_command(
    clips: list[Path], out_path: Path, *, width: int, height: int,
    clip_meta: list[dict], music: Path | None = None,
) -> list[str]:
    """ffmpeg-Argumentliste: Clips normalisieren → concat MIT Ton → (Musik ersetzt Ton).

    clip_meta[i] = {"has_audio": bool, "duration": float} (gleiche Reihenfolge
    wie clips). Wirft ValueError bei leerer/inkonsistenter Liste.
    """
    if not clips or len(clip_meta) != len(clips):
        raise ValueError("Clips und clip_meta müssen gleich lang und nicht leer sein.")

    n = len(clips)
    args: list[str] = ["ffmpeg", "-y"]
    for clip in clips:
        args += ["-i", str(clip)]
    # Eine stille Audio-Quelle für tonlose Clips (Input-Index n).
    silence_idx = n
    args += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    if music is not None:
        args += ["-i", str(music)]
        music_idx = n + 1

    parts = [_norm_chain(i, width, height, f"v{i}") for i in range(n)]
    use_clip_audio = music is None
    if use_clip_audio:
        parts += [
            _audio_chain(i, bool(clip_meta[i].get("has_audio")),
                         float(clip_meta[i].get("duration") or 0), silence_idx, f"a{i}")
            for i in range(n)
        ]
        inter = "".join(f"[v{i}][a{i}]" for i in range(n))
        parts.append(f"{inter}concat=n={n}:v=1:a=1[outv][outa]")
    else:
        inter = "".join(f"[v{i}]" for i in range(n))
        parts.append(f"{inter}concat=n={n}:v=1:a=0[outv]")
        parts.append(f"[{music_idx}:a]afade=t=out:st=0:d=99999[outa]")

    args += ["-filter_complex", ";".join(parts), "-map", "[outv]", "-map", "[outa]"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac"]
    if music is not None:
        args += ["-shortest"]
    args += [str(out_path)]
    return args
