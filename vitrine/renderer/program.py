"""Was das Display gerade zeigen soll: Nachtmodus vor Kalender; Kalender wählt Video(s), Rotation wählt eines."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from . import calendar, night
from .video import EXTS


@dataclass
class Program:
    video: Path | None = None
    rule: str | None = None
    holiday: str | None = None
    night: str | None = None          # None | "dim" | "off"

    def key(self) -> tuple:
        """Ändert sich der Schlüssel, schaltet der Dienst um und meldet den neuen Stand (Uhr/Status ändern ihn nicht)."""
        return (str(self.video) if self.video else None, self.rule, self.holiday, self.night)


def available(data_dir: Path) -> set[str]:
    try:
        return {p.name for p in (data_dir / "videos").iterdir()
                if p.is_file() and p.suffix.lower() in EXTS and not p.name.startswith(".")}
    except OSError:
        return set()


def current(data_dir: Path, config: dict, now: dt.datetime) -> Program:
    n = config.get("night") or {}
    if night.active(n, now):
        return Program(night=n.get("mode") if n.get("mode") in ("dim", "off") else "dim")
    choice = calendar.choose(config, now, available(data_dir))
    name = calendar.rotate(choice.videos, now, int(config.get("rotate_minutes") or 0))
    return Program(video=(data_dir / "videos" / name) if name else None, rule=choice.rule, holiday=choice.holiday)
