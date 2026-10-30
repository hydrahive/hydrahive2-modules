"""Aufträge des Labors (PLAN-L1.md). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations

JOBS: dict = {}


async def create(report) -> None:
    raise NotImplementedError


async def remove(report) -> None:
    raise NotImplementedError


async def reset(report) -> None:
    raise NotImplementedError


async def probe(report) -> None:
    raise NotImplementedError


async def test(report) -> None:
    raise NotImplementedError


def start(name: str) -> bool:
    raise NotImplementedError
