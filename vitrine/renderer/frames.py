"""Bild-Helfer für den Dienst: JPEG kodieren, Ersatzbild ohne Video, echte Display-Verbindung."""
from __future__ import annotations

import io

from PIL import Image

from . import aic


def encode(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def fallback_frame(w: int, h: int) -> Image.Image:
    """Ohne Video: ruhiger dunkler Verlauf (Uhr/Status liegen darüber)."""
    top, bottom = (12, 18, 32), (24, 40, 64)
    grad = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), grad)


def _connect_real():
    dev = aic.find()
    return aic.Display.open(dev) if dev is not None else None
