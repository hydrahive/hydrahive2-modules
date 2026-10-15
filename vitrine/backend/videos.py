"""Videos im Modul-Datenordner: Liste, Upload (geprüft), Löschen. Nur flache Dateinamen, nie Pfade."""
from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from pathlib import Path

EXTS = {".mp4", ".webm", ".mkv", ".mov"}
MAX_BYTES = 500 * 1024 * 1024
_SAFE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,120}$")


class VideoError(ValueError):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status, self.code = status, code


def clean_name(filename: str) -> str:
    stem, dot, ext = filename.rpartition(".")
    ext = f".{ext.lower()}" if dot else ""
    if ext not in EXTS:
        raise VideoError(400, "vitrine_video_type")
    s = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80] or "video"
    return s + ext


def safe_existing(folder: Path, name: str) -> Path:
    if not _SAFE.match(name) or Path(name).suffix.lower() not in EXTS:
        raise VideoError(400, "vitrine_video_name")
    p = folder / name
    if not p.is_file():
        raise VideoError(404, "vitrine_video_not_found")
    return p


def probe(path: Path) -> dict:
    """ffprobe: ist es ein abspielbares Video? (Dauer, Größe)"""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height:format=duration", "-of", "json", str(path)],
                             capture_output=True, text=True, timeout=30)
        d = json.loads(out.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        return {"ok": out.returncode == 0 and bool(st.get("width")), "duration": float(d.get("format", {}).get("duration") or 0),
                "width": st.get("width"), "height": st.get("height")}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"ok": False, "duration": 0.0, "width": None, "height": None}


def listing(folder: Path) -> list[dict]:
    try:
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS and not p.name.startswith("."))
    except OSError:
        return []
    return [{"name": p.name, "size": p.stat().st_size, "modified": p.stat().st_mtime} for p in files]


def store(folder: Path, filename: str, data: bytes) -> str:
    name = clean_name(filename)
    if not data:
        raise VideoError(400, "vitrine_video_empty")
    if len(data) > MAX_BYTES:
        raise VideoError(413, "vitrine_video_too_large")
    folder.mkdir(parents=True, exist_ok=True)
    stem, ext = name[: -len(Path(name).suffix)], Path(name).suffix
    final, n = name, 2
    while (folder / final).exists():
        final, n = f"{stem}-{n}{ext}", n + 1
    tmp = folder / f".upload-{final}"
    tmp.write_bytes(data)
    if not probe(tmp)["ok"]:
        tmp.unlink(missing_ok=True)
        raise VideoError(400, "vitrine_video_invalid")
    tmp.replace(folder / final)
    return final
