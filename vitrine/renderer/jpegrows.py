"""JPEG zeilenweise bearbeiten: kodieren mit Restart-Marker je MCU-Zeile, zerlegen, Zeilen tauschen, zusammensetzen.

Restart-Marker setzen die DC-Vorhersage zurück, deshalb ist jede MCU-Zeile (16 px bei 4:2:0) eigenständig.
Weil Pillow ohne `optimize` immer die Standard-Huffman-Tabellen nutzt, sind die Bytes einer Zeile nur von ihren Pixeln
und der Qualität abhängig. Getauschte Zeilen ergeben dadurch exakt das JPEG, das eine volle Kodierung liefern würde.
Erlaubt ist nur, was `encode` selbst erzeugt: Baseline (SOF0), Luma 2×2 / Chroma 1×1, ein Restart je Zeile.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

from PIL import Image

MCU = 16
_MARKER = re.compile(rb"\xff(?!\x00)[\x00-\xff]")     # im Datenstrom: alles außer FF 00 (Füllbyte)


class RowsError(ValueError):
    pass


@dataclass(frozen=True)
class Rows:
    head: bytes                 # SOI … SOS inklusive
    segments: tuple[bytes, ...]
    width: int
    height: int
    sof_at: int                 # Position der Höhe im SOF0-Segment (2 Byte)

    def tables(self) -> bytes:
        """Kopf ohne Höhe – muss beim Tauschen gleich sein (gleiche Tabellen, Breite, Qualität)."""
        return self.head[: self.sof_at] + self.head[self.sof_at + 2:]


def encode(img: Image.Image, quality: int) -> bytes:
    b = io.BytesIO()
    img.save(b, "JPEG", quality=quality, subsampling=2, restart_marker_rows=1)
    return b.getvalue()


def _rows_for(height: int) -> int:
    return (height + MCU - 1) // MCU


def split(jpeg: bytes) -> Rows:
    if len(jpeg) < 4 or jpeg[:2] != b"\xff\xd8":
        raise RowsError("kein JPEG")
    i, width, height, sof_at, dri, mcus_x = 2, 0, 0, -1, 0, 0
    while True:
        if i + 4 > len(jpeg) or jpeg[i] != 0xFF:
            raise RowsError("Kopf kaputt")
        m, ln = jpeg[i + 1], int.from_bytes(jpeg[i + 2:i + 4], "big")
        seg = jpeg[i + 4:i + 2 + ln]          # zu kurz → nächster Durchlauf meldet „Kopf kaputt“
        if m in (0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            raise RowsError("nur Baseline-JPEG")
        if m == 0xC0:
            height, width, n = int.from_bytes(seg[1:3], "big"), int.from_bytes(seg[3:5], "big"), seg[5]
            samp = [seg[6 + 3 * k + 1] for k in range(n)]
            if n != 3 or samp != [0x22, 0x11, 0x11]:
                raise RowsError("nur YCbCr 4:2:0")
            sof_at, mcus_x = i + 5, (width + MCU - 1) // MCU
        elif m == 0xDD:
            dri = int.from_bytes(seg[:2], "big")
        elif m == 0xDA:
            i += 2 + ln
            break
        i += 2 + ln
    if sof_at < 0 or not width or not height:
        raise RowsError("kein SOF0")
    if dri != mcus_x:
        raise RowsError("kein Restart je Zeile")
    if jpeg[-2:] != b"\xff\xd9":
        raise RowsError("Ende fehlt")
    body, segs, start = jpeg[i:-2], [], 0
    for k, mk in enumerate(_MARKER.finditer(body)):
        if mk.group()[1] != 0xD0 + (k % 8):
            raise RowsError("unerwarteter Marker im Bild")
        segs.append(body[start:mk.start()])
        start = mk.end()
    segs.append(body[start:])
    if len(segs) != _rows_for(height):
        raise RowsError(f"{len(segs)} Zeilen statt {_rows_for(height)}")
    return Rows(jpeg[:i], tuple(segs), width, height, sof_at)


def _join(head: bytes, segs) -> bytes:
    out = [head]
    for k, s in enumerate(segs):
        if k:
            out.append(bytes((0xFF, 0xD0 + ((k - 1) % 8))))
        out.append(s)
    out.append(b"\xff\xd9")
    return b"".join(out)


def join(rows: Rows) -> bytes:
    return _join(rows.head, rows.segments)


def strip_jpeg(rows: Rows, r0: int, r1: int) -> bytes:
    """JPEG nur der Zeilen r0..r1-1 (zum Dekodieren eines Streifens)."""
    if not 0 <= r0 < r1 <= len(rows.segments):
        raise RowsError("Zeilen außerhalb")
    h = min(rows.height, r1 * MCU) - r0 * MCU
    head = rows.head[: rows.sof_at] + h.to_bytes(2, "big") + rows.head[rows.sof_at + 2:]
    return _join(head, rows.segments[r0:r1])


def decode_rows(rows: Rows, r0: int, r1: int) -> Image.Image:
    """Pixel der Zeilen r0..r1-1, identisch zum Dekodieren des ganzen Bildes.

    Die Farb-Hochrechnung (4:2:0) nutzt die Nachbarzeile – deshalb je eine Zeile Rand mitdekodieren und abschneiden.
    """
    if not 0 <= r0 < r1 <= len(rows.segments):
        raise RowsError("Zeilen außerhalb")
    a, b = max(0, r0 - 1), min(len(rows.segments), r1 + 1)
    img = Image.open(io.BytesIO(strip_jpeg(rows, a, b)))
    img.load()
    top = (r0 - a) * MCU
    return img.convert("RGB").crop((0, top, rows.width, top + min(rows.height, r1 * MCU) - r0 * MCU))


def replace(rows: Rows, r0: int, strip: Rows) -> Rows:
    """Zeilen ab r0 durch die Zeilen von strip ersetzen (gleiche Breite und Tabellen)."""
    n = len(strip.segments)
    if strip.width != rows.width or strip.tables() != rows.tables():
        raise RowsError("Streifen passt nicht (Breite/Qualität)")
    if not 0 <= r0 or r0 + n > len(rows.segments):
        raise RowsError("Streifen ragt aus dem Bild")
    if r0 + n < len(rows.segments) and strip.height != n * MCU:
        raise RowsError("Streifen muss volle Zeilen haben")
    segs = rows.segments[:r0] + strip.segments + rows.segments[r0 + n:]
    return Rows(rows.head, segs, rows.width, rows.height, rows.sof_at)
