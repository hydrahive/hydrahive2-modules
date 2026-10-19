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
    """In Millisekunden. Die Daten sind schon auf ms gerundet und ohne Überlappung (subtitles.clean_cues)."""
    return [(_ms(c["start"]), _ms(c["end"])) for c in cues]


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


ISO639_2 = {"de": "ger", "en": "eng", "fr": "fre", "es": "spa", "it": "ita", "nl": "dut", "pl": "pol", "pt": "por", "tr": "tur",
            "uk": "ukr", "ru": "rus", "sv": "swe", "da": "dan", "no": "nor", "fi": "fin", "cs": "cze", "ja": "jpn", "zh": "chi"}


def iso639_2(lang: str) -> str:
    """Sprachkennung, wie MP4-Spieler sie für Untertitelspuren erwarten (ISO 639-2/B)."""
    return ISO639_2.get(lang, "und")


def subtitle_args(subs: list[dict], first_input: int, default_language: str) -> tuple[list[str], list[str]]:
    """Untertitel als eigene, abschaltbare Spuren (mov_text) – nie eingebrannt (Spec 6c). (Eingaben, Zuordnung)"""
    inputs, mapping = [], []
    for k, s in enumerate(subs):
        inputs += ["-i", str(s["file"])]
        mapping += ["-map", f"{first_input + k}:0", f"-metadata:s:s:{k}", f"language={iso639_2(s['language'])}",
                    f"-disposition:s:{k}", "default" if s["language"] == default_language else "0"]
    return inputs, (["-c:s", "mov_text", *mapping] if subs else [])
