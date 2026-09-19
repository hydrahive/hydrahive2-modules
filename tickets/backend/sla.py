"""Deterministic calendar-time SLA calculations for internal tickets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class SlaProfile:
    id: str = "default"
    name: str = "Default"
    urgent_response_hours: int = 4
    urgent_resolution_hours: int = 24
    high_response_hours: int = 8
    high_resolution_hours: int = 72
    normal_response_hours: int = 24
    normal_resolution_hours: int = 120
    low_response_hours: int = 72
    low_resolution_hours: int = 240

    def windows(self, priority: str) -> tuple[int, int]:
        values = {
            "urgent": (self.urgent_response_hours, self.urgent_resolution_hours),
            "high": (self.high_response_hours, self.high_resolution_hours),
            "normal": (self.normal_response_hours, self.normal_resolution_hours),
            "low": (self.low_response_hours, self.low_resolution_hours),
        }
        try:
            return values[priority]
        except KeyError as exc:
            raise ValueError("invalid_priority") from exc


def default_profile() -> SlaProfile:
    return SlaProfile()


def profile_from_row(row: Any) -> SlaProfile:
    if row is None:
        return default_profile()
    values = dict(row)
    return SlaProfile(
        id=values["id"],
        name=values["name"],
        urgent_response_hours=values["urgent_response_hours"],
        urgent_resolution_hours=values["urgent_resolution_hours"],
        high_response_hours=values["high_response_hours"],
        high_resolution_hours=values["high_resolution_hours"],
        normal_response_hours=values["normal_response_hours"],
        normal_resolution_hours=values["normal_resolution_hours"],
        low_response_hours=values["low_response_hours"],
        low_resolution_hours=values["low_resolution_hours"],
    )


def _as_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def calculate_deadlines(
    started_at: datetime | str,
    priority: str,
    profile: SlaProfile | None = None,
) -> dict[str, str]:
    response_hours, resolution_hours = (profile or default_profile()).windows(priority)
    start = _as_utc(started_at)
    return {
        "response_due_at": _format(start + timedelta(hours=response_hours)),
        "resolution_due_at": _format(start + timedelta(hours=resolution_hours)),
    }


def effective_deadline(sla_due_at: str | None, manual_due_at: str | None) -> tuple[str | None, str]:
    if manual_due_at:
        return manual_due_at, "manual"
    if sla_due_at:
        return sla_due_at, "sla"
    return None, "none"
