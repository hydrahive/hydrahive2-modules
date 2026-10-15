"""Overlay auf ein gespeichertes JPEG legen: nur die MCU-Zeilen unter dem Overlay dekodieren, verrechnen, neu kodieren.

Ergebnis ist byteidentisch zu „ganzes JPEG dekodieren → Overlay auflegen → voll kodieren“ (siehe jpegrows), kostet aber
nur einen Bruchteil, weil Uhr, Leiste und Karten wenige Zeilen belegen.
"""
from __future__ import annotations

from PIL import Image

from . import jpegrows as jr

Band = tuple[int, int, int, int]


def bands_of(overlay: Image.Image) -> list[Band]:
    """Zusammenhängende Pixelzeilen-Bereiche, in denen das Overlay sichtbar ist (am Bild zwischengespeichert)."""
    cached = getattr(overlay, "_vitrine_rows", None)
    if cached is not None:
        return cached
    a = overlay.getchannel("A")
    w, h = overlay.size
    out: list[Band] = []
    for y in range(0, h, jr.MCU):                       # je MCU-Zeile; row_groups fasst zusammen
        y1 = min(h, y + jr.MCU)
        if a.crop((0, y, w, y1)).getbbox():
            out.append((0, y, w, y1))
    overlay._vitrine_rows = out
    return out


def row_groups(bands: list[Band], height: int) -> list[tuple[int, int]]:
    """Pixel-Bänder → MCU-Zeilengruppen [r0, r1). Überlappende und bis auf eine Zeile anliegende werden zusammengefasst
    (eine Zeile mehr kodieren ist billiger als ein zweiter Streifen mit eigenem Rand beim Dekodieren)."""
    rows = sorted((y0 // jr.MCU, -(-min(y1, height) // jr.MCU)) for _, y0, _, y1 in bands)
    out: list[list[int]] = []
    for r0, r1 in rows:
        if out and r0 <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], r1)
        else:
            out.append([r0, r1])
    return [(a, b) for a, b in out]


def apply(jpeg: bytes, overlays: list[Image.Image], quality: int) -> bytes:
    if not overlays:                                     # häufigster Fall: gespeicherte Bytes ohne jede Arbeit
        return jpeg
    rows = jr.split(jpeg)
    size = (rows.width, rows.height)
    bands: list[Band] = []
    for ov in overlays:
        if ov.size != size:
            raise ValueError(f"Overlay {ov.size} passt nicht zum Bild {size}")
        bands += bands_of(ov)
    groups = row_groups(bands, rows.height)
    if not groups:
        return jpeg
    for r0, r1 in groups:
        y0, y1 = r0 * jr.MCU, min(rows.height, r1 * jr.MCU)
        strip = jr.decode_rows(rows, r0, r1).convert("RGBA")
        for ov in overlays:
            strip.alpha_composite(ov.crop((0, y0, rows.width, y1)))
        rows = jr.replace(rows, r0, jr.split(jr.encode(strip.convert("RGB"), quality)))
    return jr.join(rows)
