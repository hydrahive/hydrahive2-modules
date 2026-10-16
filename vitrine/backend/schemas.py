"""Prüfung der Vitrine-Konfiguration (PUT /config). Regel-Logik kommt aus renderer.calendar (eine Wahrheit)."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from renderer import calendar

_VIDEO = re.compile(r"^[a-z0-9][a-z0-9._-]{0,120}\.(mp4|webm|mkv|mov)$")
_HM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Night(BaseModel):
    enabled: bool = False
    from_: str = Field("23:00", alias="from")
    to: str = "07:00"
    mode: Literal["dim", "off"] = "dim"

    model_config = {"populate_by_name": True}

    @field_validator("from_", "to")
    @classmethod
    def _hm(cls, v: str) -> str:
        if not _HM.match(v):
            raise ValueError("Uhrzeit als HH:MM")
        return v


class Config(BaseModel):
    rules: list[dict] = Field(default_factory=list, max_length=100)
    default_videos: list[str] = Field(default_factory=list, max_length=50)
    night: Night = Field(default_factory=Night)
    rotate_minutes: int = Field(10, ge=0, le=1440)
    fps: int = Field(24, ge=12, le=30)                       # Bildrate; Grenzen wie renderer.config.FPS_RANGE
    message_seconds: int = Field(15, ge=5, le=120)           # Standard-Dauer einer Einblendung

    @field_validator("rules")
    @classmethod
    def _rules(cls, rules: list[dict]) -> list[dict]:
        clean = []
        for i, r in enumerate(rules):
            errs = calendar.validate_rule(r)
            if errs:
                raise ValueError(f"Regel {i + 1}: " + "; ".join(errs))
            vids = r.get("videos") or []
            if not isinstance(vids, list) or any(not _VIDEO.match(str(v)) for v in vids):
                raise ValueError(f"Regel {i + 1}: ungültiger Videoname")
            try:
                prio = int(r.get("priority", 10))
            except (TypeError, ValueError):
                raise ValueError(f"Regel {i + 1}: Priorität muss eine Zahl sein") from None
            keep = {k: r[k] for k in ("from", "to", "season", "offset_from", "offset_to") if k in r}
            clean.append({"id": str(r.get("id") or i)[:40], "name": str(r["name"]).strip()[:60], "kind": r["kind"],
                          "enabled": bool(r.get("enabled", True)), "priority": max(0, min(prio, 100)),
                          "videos": [str(v) for v in vids], **keep})
        return clean

    @field_validator("default_videos")
    @classmethod
    def _defaults(cls, vids: list[str]) -> list[str]:
        if any(not _VIDEO.match(v) for v in vids):
            raise ValueError("ungültiger Videoname")
        return vids

    def dump(self) -> dict:
        d = self.model_dump()
        d["night"] = self.night.model_dump(by_alias=True)
        return d


class SimulateIn(BaseModel):
    at: str


class PreviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at: str = Field(min_length=10, max_length=25)

    @field_validator("at")
    @classmethod
    def _at(cls, v: str) -> str:
        import datetime as _dt
        try:
            d = _dt.datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Zeitpunkt als JJJJ-MM-TTTHH:MM") from None
        if not 1900 <= d.year <= 2100:
            raise ValueError("Jahr 1900–2100")
        return v


class MessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=280)
    title: str = Field(default="", max_length=60)
    kind: Literal["info", "success", "warning", "error"] = "info"
    seconds: int | None = Field(default=None, ge=3, le=600)
