"""ffprobe: prüfen, ob eine Datei wirklich Audio ist, und Dauer/Format lesen.

Aufruf mit Argumentliste (``create_subprocess_exec``), nie über die Shell. Muster wie videoeditor/_ffmpeg.py.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path


async def probe_audio(path: Path) -> dict | None:
    """``{"duration", "codec", "sample_rate", "channels"}`` oder ``None``, wenn es kein lesbares Audio ist."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(out.decode("utf-8", "replace"))
    except ValueError:
        return None
    stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if stream is None:
        return None
    try:
        duration = float(data.get("format", {}).get("duration") or stream.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        return None
    return {"duration": round(duration, 3), "codec": stream.get("codec_name"),
            "sample_rate": int(stream.get("sample_rate") or 0), "channels": int(stream.get("channels") or 0)}
