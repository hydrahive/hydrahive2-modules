"""Video-Editor — Output-Profile + Render-Presets.

Ein OutputProfile beschreibt das Export-Ziel (Codec/Auflösung/Qualität/Audio).
Die Presets bündeln sinnvolle Profile für typische Zwecke. Konzept inspiriert
von CuttOffl (eigene Umsetzung, reduzierte Liste).

Kern-Idee 'Nur schneiden' (passthrough): codec=source + resolution=source →
kein Re-Encode-Zwang auf Profil-Ebene, Clips bleiben wo möglich copy
(sekundenschneller, verlustfreier Export).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class OutputProfile(BaseModel):
    codec: str = Field(default="source", pattern="^(source|h264|hevc)$")
    resolution: str = Field(default="source", max_length=12)  # source|720p|1080p|2160p|WxH
    crf: int | None = Field(default=None, ge=0, le=51)
    bitrate: str | None = Field(default=None, max_length=12)  # z.B. "8M"
    audio_codec: str = Field(default="copy", pattern="^(copy|aac)$")
    audio_bitrate: str = Field(default="160k", max_length=12)


class RenderPreset(BaseModel):
    id: str
    title: str
    note: str
    profile: OutputProfile


PRESETS: list[RenderPreset] = [
    RenderPreset(
        id="passthrough", title="Nur schneiden",
        note="Quelle unverändert — keyframe-genau, kein Re-Encode, sekundenschnell",
        profile=OutputProfile(codec="source", resolution="source", audio_codec="copy"),
    ),
    RenderPreset(
        id="youtube-1080", title="YouTube 1080p",
        note="1080p H.264, 8 Mbit/s",
        profile=OutputProfile(codec="h264", resolution="1080p", bitrate="8M",
                              audio_codec="aac", audio_bitrate="192k"),
    ),
    RenderPreset(
        id="web-compact", title="Web kompakt",
        note="720p H.264 CRF 26 — klein, lädt schnell",
        profile=OutputProfile(codec="h264", resolution="720p", crf=26,
                              audio_codec="aac", audio_bitrate="128k"),
    ),
    RenderPreset(
        id="archive", title="Archiv",
        note="Quell-Auflösung, HEVC CRF 18 — sehr hohe Qualität",
        profile=OutputProfile(codec="hevc", resolution="source", crf=18,
                              audio_codec="aac", audio_bitrate="256k"),
    ),
]


def get_preset(preset_id: str) -> RenderPreset | None:
    return next((p for p in PRESETS if p.id == preset_id), None)


def _norm_vcodec(c: str | None) -> str:
    if not c:
        return ""
    c = c.lower().strip()
    if c in ("hevc", "h265", "x265"):
        return "hevc"
    if c in ("h264", "avc", "avc1", "x264"):
        return "h264"
    return c


def output_forces_reencode(profile: OutputProfile, source: dict | None) -> tuple[bool, str]:
    """Erzwingt das Ziel-Profil ein Re-Encode ALLER Clips?

    Copy-Mode kopiert den Stream 1:1 — Auflösung/Codec/Bitrate/CRF würden dann
    ignoriert. Damit 'copy' nicht am User vorbei lügt, prüfen wir streng:
      - Auflösung ≠ source → skalieren, geht nicht mit copy
      - Bitrate/CRF gesetzt → Qualitätsziel, greift nur beim Transcode
      - Ziel-Codec ≠ Quell-Codec → muss transkodiert werden
    Bei True müssen ALLE Clips reencode (concat-Demuxer braucht homogene Streams).
    """
    if profile.resolution and profile.resolution != "source":
        return True, f"Zielauflösung {profile.resolution}"
    if profile.bitrate:
        return True, f"Ziel-Bitrate {profile.bitrate}"
    if profile.crf is not None:
        return True, f"CRF {profile.crf}"
    if profile.codec != "source" and source is not None:
        src_v = _norm_vcodec(source.get("video_codec"))
        dst_v = _norm_vcodec(profile.codec)
        if src_v and dst_v and src_v != dst_v:
            return True, f"Codec-Wechsel {src_v}→{dst_v}"
    return False, ""
