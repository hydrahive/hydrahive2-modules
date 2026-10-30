"""Einrichtung im Labor-Container (PLAN-L1.md). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations

STEPS: tuple = ()


class SetupError(RuntimeError):
    def __init__(self, code: str, step: str = ""):
        super().__init__(code)
        self.code = code
        self.step = step


async def setup(report) -> None:
    raise NotImplementedError


async def snapshot() -> None:
    raise NotImplementedError


async def has_snapshot() -> bool:
    raise NotImplementedError


async def reset() -> dict:
    raise NotImplementedError
