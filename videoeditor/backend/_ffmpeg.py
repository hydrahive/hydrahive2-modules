"""Video-Editor — ffmpeg/ffprobe-Kommando-Bau.

Alle Aufrufe über ``asyncio.create_subprocess_exec`` mit Argumenten als LISTE
(kein ``shell=True``) — keine Shell-Injection möglich, analog zum
atelier/backend/_ffmpeg.py-Muster.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

PROXY_HEIGHT = 480


class FFmpegError(RuntimeError):
    pass


async def run(*args: str) -> tuple[int, bytes, bytes]:
    """Öffentlicher Alias für _run — von export_service.py genutzt."""
    return await _run(*args)


async def _run(*args: str) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out, err


async def probe(video: Path) -> dict:
    """Liefert {duration, fps, width, height, has_audio} via ffprobe."""
    rc, out, err = await _run(
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(video),
    )
    if rc != 0:
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])
    data = json.loads(out.decode("utf-8", "replace"))
    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    fps_raw = v_stream.get("r_frame_rate", "25/1")
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den) if float(den) else 25.0
    except (ValueError, ZeroDivisionError):
        fps = 25.0
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "fps": round(fps, 3),
        "width": int(v_stream.get("width") or 0),
        "height": int(v_stream.get("height") or 0),
        "has_audio": has_audio,
    }


async def keyframe_timestamps(video: Path) -> list[float]:
    """Zeitstempel aller I-Frames (Keyframes) — Grundlage für den
    Keyframe-Magnet in der Timeline (verlustfreier Schnitt nur an diesen
    Punkten möglich)."""
    rc, out, err = await _run(
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "frame=pkt_pts_time,key_frame",
        "-of", "csv=print_section=0", str(video),
    )
    if rc != 0:
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])
    stamps: list[float] = []
    for line in out.decode("utf-8", "replace").splitlines():
        parts = line.strip().split(",")
        if len(parts) != 2:
            continue
        key_flag, t_raw = parts
        if key_flag != "1":
            continue
        try:
            stamps.append(float(t_raw))
        except ValueError:
            continue
    return stamps


async def make_proxy(src: Path, dst: Path) -> None:
    """480p-H.264-Proxy fürs flüssige Scrubben im Browser."""
    args = [
        "ffmpeg", "-y", "-i", str(src),
        "-vf", f"scale=-2:{PROXY_HEIGHT}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(dst),
    ]
    rc, _, err = await _run(*args)
    if rc != 0 or not dst.is_file():
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])


async def make_sprite(
    src: Path, dst: Path, *, duration: float, interval: float, cols: int,
    tile_w: int, tile_h: int,
) -> dict:
    """Filmstrip-Sprite: ein JPG-Grid mit einem Thumbnail alle ``interval``
    Sekunden — Grundlage fürs Filmstrip-Band in der Timeline.

    Die Kachelzahl (rows×cols) muss ffmpeg exakt vorgegeben werden — daher
    wird die Frame-Anzahl aus der (bereits geprobten) Videolänge berechnet.
    Returns Sprite-Metadaten (count/cols/rows/tile_w/tile_h/interval) fürs
    Frontend, um Zeit→Tile-Koordinate umzurechnen.
    """
    count = max(1, int(duration / interval) + 1)
    rows = max(1, (count + cols - 1) // cols)
    args = [
        "ffmpeg", "-y", "-i", str(src),
        "-frames:v", "1", "-q:v", "3",
        "-vf", (
            f"fps=1/{interval},scale={tile_w}:{tile_h}:force_original_aspect_ratio=decrease,"
            f"pad={tile_w}:{tile_h}:(ow-iw)/2:(oh-ih)/2,tile={cols}x{rows}"
        ),
        str(dst),
    ]
    rc, _, err = await _run(*args)
    if rc != 0 or not dst.is_file():
        raise FFmpegError(err.decode("utf-8", "replace")[-400:])
    return {"count": count, "cols": cols, "rows": rows, "tile_w": tile_w, "tile_h": tile_h, "interval": interval}
