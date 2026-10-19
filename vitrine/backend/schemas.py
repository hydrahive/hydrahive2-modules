"""Prüfung der Vitrine-Konfiguration (PUT /config). Regel-Logik kommt aus renderer.calendar (eine Wahrheit)."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from renderer import calendar, calendar_extra, config, dash_layout

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


class Dashboard(BaseModel):
    """Statuszentrale (S2 + S4). Prüfung in renderer.dash_layout – eine Wahrheit für Server und Dienst."""
    model_config = ConfigDict(extra="forbid")
    tasks_user: str = "till"
    github_project: str = "Hydrahive DEV"
    github_repos: list[str] = Field(default_factory=lambda: list(dash_layout.DEFAULTS["github_repos"]))
    order: list[str] = Field(default_factory=lambda: list(dash_layout.AREAS))
    hidden: list[str] = Field(default_factory=list)
    messages_max: StrictInt = 3
    home_rooms: list[str] = Field(default_factory=list)
    mining_in_machine: bool = True
    pages: dict[str, StrictInt] = Field(default_factory=lambda: dict(dash_layout.DEFAULT_PAGES))

    @model_validator(mode="after")
    def _ok(self):
        self.github_project = self.github_project.strip()
        if not dash_layout.layout_ok(self.model_dump()):
            raise ValueError("Statuszentrale: Einstellung ungültig (Nutzer, Projekt, Repo, Bereiche, Räume oder Grenzen)")
        return self

    def full(self) -> dict:
        return dash_layout.normalize(self.model_dump())


class Config(BaseModel):
    rules: list[dict] = Field(default_factory=list, max_length=100)
    default_videos: list[str] = Field(default_factory=list, max_length=50)
    night: Night = Field(default_factory=Night)
    rotate_minutes: int = Field(10, ge=0, le=1440)
    fps: int = Field(24, ge=12, le=30)                       # Bildrate; Grenzen wie renderer.config.FPS_RANGE
    message_seconds: int = Field(15, ge=5, le=120)           # Standard-Dauer einer Einblendung
    dashboard_return_seconds: int = Field(120, ge=30, le=1800)  # Dashboard → Video nach so vielen s ohne Eingabe
    dashboard: Dashboard = Field(default_factory=Dashboard)

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
            if r["kind"] in calendar_extra.KINDS:
                keep = calendar_extra.clean(r)          # nur die Felder der Art – kein from/to/dates-Mischmasch
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
        d["dashboard"] = self.dashboard.full()
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
