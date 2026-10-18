"""Untertitel als Datei (Spec „Bauplan Etappe 6“): SRT und WebVTT, erzeugt beim Abruf aus den Daten."""
from __future__ import annotations

import re

FORMATS = {"srt": "application/x-subrip; charset=utf-8", "vtt": "text/vtt; charset=utf-8"}


def _ms(t: float) -> int:
    return round(t * 1000)


def _stamp(ms: int, sep: str) -> str:
    h, rest = divmod(ms, 3_600_000)
    m, rest = divmod(rest, 60_000)
    s, ms = divmod(rest, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _times(cues: list[dict]) -> list[tuple[int, int]]:
    """Auf Millisekunden gerundet; ein Anfang liegt nie vor dem gerundeten Ende des Vorgängers."""
    out, last = [], 0
    for c in cues:
        a = max(_ms(c["start"]), last)
        b = max(_ms(c["end"]), a + 1)
        out.append((a, b))
        last = b
    return out


def srt(cues: list[dict]) -> str:
    blocks = [f"{n}\n{_stamp(a, ',')} --> {_stamp(b, ',')}\n{c['text']}\n"
              for n, (c, (a, b)) in enumerate(zip(cues, _times(cues), strict=True), start=1)]
    return "\n".join(blocks)


def _vtt_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def vtt(cues: list[dict]) -> str:
    blocks = [f"{_stamp(a, '.')} --> {_stamp(b, '.')}\n{_vtt_text(c['text'])}\n" for c, (a, b) in zip(cues, _times(cues), strict=True)]
    return "WEBVTT\n\n" + "\n".join(blocks)


def filename(title: str, lang: str, fmt: str) -> str:
    name = re.sub(r"[\x00-\x1f/\\:*?\"<>|]+", " ", title or "")
    name = " ".join(name.split()).strip(" .") or "Film"
    return f"{name[:80]}.{lang}.{fmt}"
