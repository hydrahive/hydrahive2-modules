"""Zustand des Labors (PLAN-L1.md „Assistent“). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations


def get() -> dict:
    raise NotImplementedError


def clear() -> None:
    raise NotImplementedError


def mark_made(part: str, **ids: str) -> None:
    raise NotImplementedError


def begin(job: str) -> bool:
    raise NotImplementedError


def progress(key: str) -> None:
    raise NotImplementedError


def finish(*, error_code: str = "", error_step: str = "") -> None:
    raise NotImplementedError


def save_choice(*, model: str, cpu: int, ram_mb: int, disk_gb: int) -> None:
    raise NotImplementedError


def set_step(step: str) -> None:
    raise NotImplementedError


def net_ok() -> None:
    raise NotImplementedError


def recover_after_restart() -> None:
    raise NotImplementedError
