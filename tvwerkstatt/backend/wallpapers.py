"""Hintergrundbilder je Fernseher und Tageszeit (PLAN-E2.md Baustein C).

Hochgeladene Bilder werden auf dem Server mit Pillow geöffnet (nur JPEG/PNG/WebP), auf 1920×1080 zugeschnitten und als
JPEG gespeichert (Ziel ≤ ca. 300 KB laut themes/README.md). Der Dateiname wird vom Server vergeben, nie vom Nutzer.
"""
from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from hydrahive.db.connection import db
from hydrahive.settings import settings

from .look import MOODS

MAX_UPLOAD = 15_000_000
MAX_PER_DEVICE = 30
W, H = 1920, 1080
TARGET = 300_000
_COLS = ("wallpaper_id", "mood", "file_name", "title", "sha256", "created_at")


class TvwWallpaperError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def folder(device_id: str) -> Path:
    return settings.data_dir / "tvwerkstatt" / "wallpapers" / device_id


def prepare(data: bytes) -> bytes:
    """Bild lesen, auf 16:9 zuschneiden, verkleinern, als JPEG unter ca. 300 KB."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not data or len(data) > MAX_UPLOAD:
        raise TvwWallpaperError("tvw_image_too_large" if data else "tvw_image_invalid")
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in ("JPEG", "PNG", "WEBP"):
                raise TvwWallpaperError("tvw_image_invalid")
            if im.width * im.height > 60_000_000:
                raise TvwWallpaperError("tvw_image_too_large")
            im = ImageOps.exif_transpose(im).convert("RGB")
            im = ImageOps.fit(im, (W, H), method=Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise TvwWallpaperError("tvw_image_invalid") from None
    for q in (85, 78, 70, 62, 55):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= TARGET:
            break
    return buf.getvalue()


def add(device_id: str, mood: str, data: bytes, title: str = "") -> dict:
    if mood not in MOODS:
        raise TvwWallpaperError("tvw_look_invalid")
    if len(list_for(device_id)) >= MAX_PER_DEVICE:
        raise TvwWallpaperError("tvw_too_many_images")
    jpg = prepare(data)
    wid = uuid.uuid4().hex[:12]
    name = f"{mood}-{wid}.jpg"
    folder(device_id).mkdir(parents=True, exist_ok=True)
    (folder(device_id) / name).write_bytes(jpg)
    clean_title = "".join(c for c in str(title or "") if c.isprintable())[:60]
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_wallpapers (wallpaper_id, device_id, mood, file_name, title, sha256) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (wid, device_id, mood, name, clean_title, hashlib.sha256(jpg).hexdigest()))
        conn.commit()
    return next(w for w in list_for(device_id) if w["wallpaper_id"] == wid)


def list_for(device_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(_COLS)} FROM module_tvwerkstatt_wallpapers WHERE device_id = ? "
                            "ORDER BY created_at, wallpaper_id", (device_id,)).fetchall()
    return [dict(zip(_COLS, r, strict=True)) for r in rows]


def remove(device_id: str, wallpaper_id: str) -> None:
    w = next((x for x in list_for(device_id) if x["wallpaper_id"] == wallpaper_id), None)
    if w is None:
        raise TvwWallpaperError("tvw_image_not_found")
    with db() as conn:
        conn.execute("DELETE FROM module_tvwerkstatt_wallpapers WHERE device_id = ? AND wallpaper_id = ?",
                     (device_id, wallpaper_id))
        conn.commit()
    (folder(device_id) / w["file_name"]).unlink(missing_ok=True)


def by_mood(device_id: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {m: [] for m in MOODS}
    for w in list_for(device_id):
        if (folder(device_id) / w["file_name"]).is_file():
            out[w["mood"]].append(w["file_name"])
    return {m: v for m, v in out.items() if v}
