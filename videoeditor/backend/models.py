"""Video-Editor — EDL-Datenmodell (Edit Decision List).

Ein Clip beschreibt einen Ausschnitt des Quellvideos (src_start..src_end) und
den gewünschten Render-Modus. "copy" ist nur an Keyframe-Grenzen verlustfrei
möglich (Hybrid-Export prüft das serverseitig nach, "mode" ist der
Nutzerwunsch, nicht die Garantie).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Clip(BaseModel):
    id: str
    src_start: float = Field(ge=0)
    src_end: float = Field(gt=0)
    mode: str = Field(default="reencode", pattern="^(copy|reencode)$")


class EDL(BaseModel):
    file_id: str
    timeline: list[Clip] = Field(default_factory=list)

    def sanitized(self) -> "EDL":
        """Sortiert nach src_start, verwirft leere/invertierte Clips."""
        clean = [c for c in self.timeline if c.src_end > c.src_start]
        clean.sort(key=lambda c: c.src_start)
        return EDL(file_id=self.file_id, timeline=clean)


class VideoMeta(BaseModel):
    file_id: str
    filename: str
    source_rel: str  # workspace-relativer Pfad zum Original (bleibt im Projekt!)
    duration: float
    fps: float
    width: int
    height: int
    has_audio: bool
    keyframes: list[float] = Field(default_factory=list)
    sprite: dict | None = None
    edl: EDL | None = None
