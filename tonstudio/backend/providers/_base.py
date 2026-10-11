"""Schnittstelle der Musik-Anbieter (SPEC.md §5.6).

Jeder Anbieter ist ein Adapter mit ``list_models()`` und ``generate()``. Ein Modell meldet seine Fähigkeiten.
Die Oberfläche zeigt nur, was das gewählte Modell kann. Unbekannte Werte werden NICHT behauptet (``None``/``False``).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from ..prompt import MusicRequest


class ProviderError(RuntimeError):
    """Erzeugen fehlgeschlagen (kein Schlüssel, Anbieter-Fehler, leere Antwort). Text ist für Menschen."""


@dataclass(frozen=True)
class MusicModel:
    id: str
    name: str
    backend: str
    lyrics: bool = False                 # eigener Liedtext wird gesungen
    image_ref: bool = False              # Bilder als Referenz
    audio_ref: bool = False              # Audiodatei als Referenz
    instrumental_switch: bool = False    # instrumental zuverlässig erzwingbar
    max_seconds: int | None = None       # None = unbekannt
    local: bool = False
    price_note: str = "Kosten unbekannt"
    license_note: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MusicResult:
    audio: bytes
    ext: str
    text: str = ""                       # vom Modell zurückgegebener Text (z. B. Liedtext, Struktur)
    prompt: str = ""                     # tatsächlich gesendeter Prompt (Provenienz)


class MusicBackend(Protocol):
    name: str

    async def list_models(self) -> list[MusicModel]: ...

    async def generate(self, model_id: str, req: MusicRequest) -> MusicResult: ...
