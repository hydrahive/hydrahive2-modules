"""Fehler melden (PLAN-L2.md Baustein 6). Platzhalter."""
from __future__ import annotations


def _environment() -> dict:
    raise NotImplementedError


async def report(target: str, title: str, what: str, expected: str, steps: str) -> dict:
    raise NotImplementedError
