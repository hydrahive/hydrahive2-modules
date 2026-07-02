"""Video-Editor — EDL-Datenmodell (Edit Decision List).

Ein Clip beschreibt einen Ausschnitt des Quellvideos (src_start..src_end) und
den gewünschten Render-Modus. "copy" ist nur an Keyframe-Grenzen verlustfrei
möglich (Hybrid-Export prüft das serverseitig nach, "mode" ist der
Nutzerwunsch, nicht die Garantie).

Nachvertonung (SPEC-AUDIO.md): zusätzlich zum Video-Ton (``original_audio``)
können mehrere ``AudioTrack``s mit platzierten ``AudioClip``s definiert werden.
Alte EDLs ohne Audio-Felder bleiben gültig — die Felder haben Defaults, der
Export fällt dann auf den O-Ton-Passthrough-Pfad zurück.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Clip(BaseModel):
    id: str
    src_start: float = Field(ge=0)
    src_end: float = Field(gt=0)
    mode: str = Field(default="reencode", pattern="^(copy|reencode)$")


class AudioClip(BaseModel):
    """Ein platzierter Audio-Ausschnitt auf einer Audiospur.

    ``t_start`` = Position auf der Timeline (Sekunden). ``src_start``/``src_end``
    = Ausschnitt aus der Quelldatei. ``gain_db`` + Fades wirken pro Clip.
    """
    id: str
    source_rel: str = Field(min_length=1, max_length=500)  # workspace-relativ
    t_start: float = Field(default=0.0, ge=0)
    src_start: float = Field(default=0.0, ge=0)
    src_end: float = Field(gt=0)
    gain_db: float = 0.0
    fade_in: float = Field(default=0.0, ge=0)
    fade_out: float = Field(default=0.0, ge=0)


class AudioTrack(BaseModel):
    id: str
    name: str = Field(default="Audio", max_length=80)
    mute: bool = False
    solo: bool = False
    gain_db: float = 0.0
    clips: list[AudioClip] = Field(default_factory=list)

    def sanitized(self) -> "AudioTrack":
        """Verwirft leere/invertierte Clips, sortiert nach Timeline-Position."""
        clean = [c for c in self.clips if c.src_end > c.src_start]
        clean.sort(key=lambda c: c.t_start)
        return AudioTrack(
            id=self.id, name=self.name, mute=self.mute, solo=self.solo,
            gain_db=self.gain_db, clips=clean,
        )


class OriginalAudio(BaseModel):
    """Der Ton aus dem geschnittenen Video (Spur 0)."""
    mute: bool = False
    gain_db: float = 0.0


class EDL(BaseModel):
    file_id: str
    timeline: list[Clip] = Field(default_factory=list)
    original_audio: OriginalAudio = Field(default_factory=OriginalAudio)
    audio: list[AudioTrack] = Field(default_factory=list)

    def sanitized(self) -> "EDL":
        """Sortiert Video-Clips nach src_start, verwirft leere/invertierte
        Clips; säubert ebenso jede Audiospur (leere Spuren bleiben erhalten,
        damit die UI-Struktur des Nutzers nicht verloren geht)."""
        clean = [c for c in self.timeline if c.src_end > c.src_start]
        clean.sort(key=lambda c: c.src_start)
        return EDL(
            file_id=self.file_id,
            timeline=clean,
            original_audio=self.original_audio,
            audio=[t.sanitized() for t in self.audio],
        )

    def has_audio_mix(self) -> bool:
        """True, wenn ein echter Audio-Mix nötig ist (Spuren mit Clips ODER
        O-Ton-Anpassung). Sonst kann der Export den Passthrough-Pfad nehmen."""
        if self.original_audio.mute or self.original_audio.gain_db != 0.0:
            return True
        return any(t.clips for t in self.audio)


class AudioMeta(BaseModel):
    """Aufbereitete Audiodatei (Sidecar) — Dauer + Verweis auf Peaks-JSON."""
    audio_id: str
    filename: str
    source_rel: str          # bleibt im Projekt-Workspace
    duration: float
    sample_rate: int = 0
    channels: int = 0


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
