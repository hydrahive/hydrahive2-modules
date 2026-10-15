"""Video-Auswahl und Schleifen-Cache.

Damit der Dienst zur Laufzeit nur noch dekodiert (wenig CPU), wird jedes Video einmal umgerechnet:
Panelgröße, Ziel-fps, ohne Ton und mit 1 s Überblendung vom Ende zum Anfang (Schleife ohne harten Sprung).
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Iterator

from PIL import Image

EXTS = {".mp4", ".webm", ".mkv", ".mov"}
FADE = 1.0


def pick(folder: Path) -> Path | None:
    """E1: erstes Video im Ordner (alphabetisch). Kalender-Regeln kommen in E2."""
    try:
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS and not p.name.startswith("."))
    except OSError:
        return None
    return files[0] if files else None


def cache_path(src: Path, cache_dir: Path, w: int, h: int, fps: int) -> Path:
    st = src.stat()
    tag = hashlib.sha1(f"{src.name}|{st.st_size}|{int(st.st_mtime)}|{w}x{h}@{fps}".encode()).hexdigest()[:12]
    return cache_dir / f"{src.stem}-{tag}.mp4"


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, timeout=30)
    return float(out.stdout.strip() or 0)


def prepare(src: Path, cache_dir: Path, w: int, h: int, fps: int) -> Path:
    out = cache_path(src, cache_dir, w, h, fps)
    if out.exists():
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    for old in cache_dir.glob(f"{src.stem}-*.mp4"):          # alte Fassungen derselben Quelle
        old.unlink(missing_ok=True)
    base = f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},fps={fps},setsar=1"
    dur = duration(src)
    if dur > 2 * FADE + 0.5:
        graph = (f"[0:v]{base}[a];[1:v]{base}[b];"
                 f"[a][b]xfade=transition=fade:duration={FADE}:offset={dur - FADE - 0.05:.2f},"
                 f"trim=start={FADE},setpts=PTS-STARTPTS")
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-i", str(src), "-filter_complex", graph]
    else:
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-vf", base]
    tmp = out.with_suffix(".tmp.mp4")
    subprocess.run([*cmd, "-an", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(tmp)],
                   check=True, timeout=900)
    tmp.replace(out)
    return out


def frames(src: Path, w: int, h: int, fps: int) -> Iterator[Image.Image]:
    """Bilder der vorbereiteten Datei in Endlosschleife (ffmpeg -stream_loop)."""
    size = w * h * 3
    proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", str(src),
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=size)
    try:
        while True:
            raw = proc.stdout.read(size)
            if len(raw) < size:
                return
            yield Image.frombytes("RGB", (w, h), raw)
    finally:
        proc.kill()
        proc.wait(timeout=5)
