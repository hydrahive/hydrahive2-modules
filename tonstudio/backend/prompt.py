"""Anbieterneutraler Musik-Auftrag und daraus der Prompt-Text (SPEC.md §5.6).

Ein Auftrag beschreibt, WAS entstehen soll (Stil, Beschreibung, Tempo, Tonart, Länge, Liedtext). Wie ein
Anbieter das umsetzt, entscheidet der Adapter. Für textbasierte Modelle (Lyria) wird daraus ein Prompt mit
fester Reihenfolge: gleichbleibender Stil zuerst, das Variable danach, der Liedtext zuletzt unter ``Lyrics:``
(Lyria-Prompt-Guide, „Lyrics and vocals“, https://ai.google.dev/gemini-api/docs/lyria-prompt-guide).
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MusicRequest(BaseModel):
    style: str = Field(default="", max_length=2000)
    description: str = Field(default="", max_length=4000)
    bpm: float | None = Field(default=None, gt=0, le=400)
    key: str | None = Field(default=None, max_length=40)
    duration_s: int | None = Field(default=None, ge=5, le=600)
    instrumental: bool = False
    lyrics: str = Field(default="", max_length=8000)

    @model_validator(mode="after")
    def _check(self) -> "MusicRequest":
        if not (self.style.strip() or self.description.strip() or self.lyrics.strip()):
            raise ValueError("Auftrag ist leer – Stil, Beschreibung oder Liedtext angeben")
        if self.instrumental and self.lyrics.strip():
            raise ValueError("Instrumental und Liedtext schließen sich aus")
        return self


def _mmss(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def build_prompt(req: MusicRequest) -> str:
    parts: list[str] = [p.strip() for p in (req.style, req.description) if p.strip()]
    if req.bpm:
        parts.append(f"{req.bpm:g} BPM")
    if req.key:
        parts.append(f"in {req.key.strip()}")
    if req.duration_s:
        parts.append(f"about {_mmss(req.duration_s)} long")
    if req.instrumental:
        parts.append("Instrumental only, no vocals")
    text = ". ".join(parts)
    if req.lyrics.strip():
        text = (text + "\n\n" if text else "") + "Lyrics:\n" + req.lyrics.strip()
    return text
