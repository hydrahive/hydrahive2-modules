"""GitHub-Zugriffe (PLAN-L2.md Baustein 7). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations

_SLEEP = 1


async def request(method: str, url: str, *, token: str = "", data: dict | None = None,
                  json: dict | None = None) -> tuple[int, dict, dict]:
    raise NotImplementedError
