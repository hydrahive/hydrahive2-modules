"""Nachtmodus: Zeitfenster (auch über Mitternacht) und das Nachtbild (dim = gedimmte Uhr, off = schwarz)."""
from __future__ import annotations

import datetime as dt

from PIL import Image, ImageDraw

from . import scene
from .calendar import _hm

DIM_GREY = (70, 70, 80)


def active(night: dict, now: dt.datetime) -> bool:
    if not night.get("enabled"):
        return False
    a, b = _hm(night.get("from")), _hm(night.get("to"))
    if a is None or b is None or a == b:
        return False
    t = now.hour * 60 + now.minute
    return a <= t < b if a < b else (t >= a or t < b)


def frame(mode: str, w: int, h: int, now: dt.datetime) -> Image.Image:
    img = Image.new("RGB", (w, h), (0, 0, 0))
    if mode != "dim":
        return img
    dr = ImageDraw.Draw(img)
    font = scene._font("DejaVuSans.ttf", int(140 * w / 1080))
    txt = now.strftime("%H:%M")
    dr.text(((w - dr.textlength(txt, font=font)) / 2, h * 0.42), txt, font=font, fill=DIM_GREY)
    return img
