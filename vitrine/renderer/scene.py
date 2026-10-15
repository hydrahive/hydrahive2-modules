"""Overlay über dem Video: Uhr + Datum oben, Status-Leiste unten. Die Mitte bleibt frei (Figuren davor).

Das Overlay wird nur neu gezeichnet, wenn sich Uhrzeit (Minute), Datum oder Status ändern; pro Video-Bild
wird es nur noch per alpha_composite aufgelegt.
"""
from __future__ import annotations

import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember")
_FONTS = Path("/usr/share/fonts/truetype/dejavu")
WHITE, SHADOW, CYAN, BAR = (255, 255, 255, 235), (0, 0, 0, 120), (150, 225, 255, 240), (10, 14, 24, 150)
GOLD = (255, 214, 120, 240)


def clock_text(t: time.struct_time) -> str:
    return time.strftime("%H:%M", t)


def date_text(t: time.struct_time) -> str:
    return f"{TAGE[t.tm_wday]}, {t.tm_mday}. {MONATE[t.tm_mon - 1]}"


def _font(name: str, size: int):
    try:
        return ImageFont.truetype(str(_FONTS / name), size)
    except OSError:
        return ImageFont.load_default(size)


class Overlay:
    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        u = width / 1080
        self.clock_font = _font("DejaVuSans-Bold.ttf", int(200 * u))
        self.date_font = _font("DejaVuSans.ttf", int(56 * u))
        self.small_font = _font("DejaVuSans.ttf", int(38 * u))
        self.u = u
        self._key: tuple | None = None
        self._img: Image.Image | None = None

    def render(self, t: time.struct_time, status: str, holiday: str | None = None) -> Image.Image:
        key = (clock_text(t), date_text(t), status, holiday)
        if key == self._key and self._img is not None:
            return self._img
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        self._centered(dr, key[0], self.clock_font, int(120 * self.u), WHITE)
        self._centered(dr, key[1], self.date_font, int(360 * self.u), WHITE)
        if holiday:
            self._centered(dr, holiday, self.date_font, int(450 * self.u), GOLD)
        if status:
            m = int(40 * self.u)
            dr.rounded_rectangle([m, self.h - int(120 * self.u), self.w - m, self.h - m], int(28 * self.u), fill=BAR)
            tw = dr.textlength(status, font=self.small_font)
            dr.text(((self.w - tw) / 2, self.h - int(103 * self.u)), status, font=self.small_font, fill=CYAN)
        self._key, self._img = key, img
        return img

    def _centered(self, dr: ImageDraw.ImageDraw, text: str, font, y: int, fill) -> None:
        x = (self.w - dr.textlength(text, font=font)) / 2
        off = max(2, int(4 * self.u))
        dr.text((x + off, y + off), text, font=font, fill=SHADOW)
        dr.text((x, y), text, font=font, fill=fill)


def _bands(overlay: Image.Image) -> list[tuple[int, int, int, int]]:
    """Waagrechte Streifen, in denen das Overlay etwas zeichnet (oben Uhr/Datum, unten Leiste)."""
    a = overlay.getchannel("A")
    w, h = overlay.size
    top = a.crop((0, 0, w, h // 2)).getbbox()
    bot = a.crop((0, h // 2, w, h)).getbbox()
    out = []
    if top:
        out.append((0, top[1], w, top[3]))
    if bot:
        out.append((0, h // 2 + bot[1], w, h // 2 + bot[3]))
    return out


def compose(frame: Image.Image, overlay: Image.Image) -> Image.Image:
    """Overlay auflegen – nur in den Streifen, wo es etwas zeichnet (spart ~2/3 der Rechenzeit)."""
    out = frame.copy() if frame.mode == "RGB" else frame.convert("RGB")
    bands = getattr(overlay, "_vitrine_bands", None)
    if bands is None:
        bands = _bands(overlay)
        overlay._vitrine_bands = bands
    for box in bands:
        part = Image.alpha_composite(out.crop(box).convert("RGBA"), overlay.crop(box))
        out.paste(part.convert("RGB"), box[:2])
    return out
