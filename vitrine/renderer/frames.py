"""Bild-Helfer für den Dienst: JPEG kodieren, Vorschau schreiben, Ersatzbild ohne Video, echte Display-Verbindung."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from . import aic


def encode(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


PREVIEW_SIZE = (270, 480)


def write_preview(data: Path, jpeg: bytes, img: Image.Image | None = None) -> None:
    """<data>/preview.jpg (270×480). Ohne fertiges Bild (Cache-Weg) wird das JPEG verkleinert dekodiert."""
    if img is None:
        img = Image.open(io.BytesIO(jpeg))
        img.draft("RGB", (PREVIEW_SIZE[0] * 2, PREVIEW_SIZE[1] * 2))
    tmp = data / "preview.jpg.tmp"
    img.convert("RGB").resize(PREVIEW_SIZE).save(tmp, "JPEG", quality=80)
    tmp.replace(data / "preview.jpg")


def fallback_frame(w: int, h: int) -> Image.Image:
    """Ohne Video: ruhiger dunkler Verlauf (Uhr/Status liegen darüber)."""
    top, bottom = (12, 18, 32), (24, 40, 64)
    grad = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), grad)


def _connect_real():
    dev = aic.find()
    return aic.Display.open(dev) if dev is not None else None
