"""L3: eingehende Regel für die Probe. Platzhalter."""
from __future__ import annotations

PORT = 0


async def open_port() -> None:
    raise NotImplementedError


async def close_port() -> None:
    raise NotImplementedError


async def is_open() -> bool:
    raise NotImplementedError
