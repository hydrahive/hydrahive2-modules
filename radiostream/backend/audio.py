"""Vorhören im Browser: MP3 direkt (mit Range), andere Formate per ffmpeg nach MP3 192k umgewandelt.

Die Datei wird per SMB gelesen und durchgereicht – keine Zwischendatei, nichts auf dem NAS geändert.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from collections.abc import Iterator

logger = logging.getLogger(__name__)
CHUNK = 64 * 1024
DIRECT = {"mp3": "audio/mpeg"}


def _copy_in(src, proc: subprocess.Popen) -> None:
    try:
        while chunk := src.read(CHUNK):
            proc.stdin.write(chunk)  # type: ignore[union-attr]
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            proc.stdin.close()  # type: ignore[union-attr]
        except OSError:
            pass


def transcode_mp3(src, fmt: str) -> Iterator[bytes]:
    """Beliebiges Audio → MP3 192k (ffmpeg liest stdin, schreibt stdout)."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    proc = subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", fmt if fmt != "m4a" else "mov",
                             "-i", "pipe:0", "-vn", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", "pipe:1"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    feeder = threading.Thread(target=_copy_in, args=(src, proc), daemon=True)
    feeder.start()
    try:
        while chunk := proc.stdout.read(CHUNK):  # type: ignore[union-attr]
            yield chunk
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        feeder.join(timeout=2)


def read_range(fh, start: int, end: int) -> Iterator[bytes]:
    fh.seek(start)
    left = end - start + 1
    while left > 0:
        chunk = fh.read(min(CHUNK, left))
        if not chunk:
            break
        left -= len(chunk)
        yield chunk
