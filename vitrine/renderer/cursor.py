"""Mauszeiger für das Dashboard-Bild. EVDI liefert nur den Bildschirminhalt ohne Zeiger (am 18.10.2026 gesehen),
deshalb zeichnet Vitrine einen einfachen Pfeil an die Position, die der X-Server meldet."""
from __future__ import annotations

from PIL import Image, ImageDraw

FILL, EDGE = (255, 255, 255), (0, 0, 0)
SCALE = 2                      # vom Sofa sichtbar: doppelte Größe eines normalen Zeigers
_ARROW = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]


def draw(img: Image.Image, pos: tuple[int, int]) -> None:
    x, y = pos
    if not (0 <= x < img.width and 0 <= y < img.height):
        return
    pts = [(x + px * SCALE, y + py * SCALE) for px, py in _ARROW]
    ImageDraw.Draw(img).polygon(pts, fill=FILL, outline=EDGE, width=2)
