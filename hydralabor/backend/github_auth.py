"""GitHub verbinden (PLAN-L2.md Baustein 1). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations

import asyncio  # noqa: F401
import time

CLIENT_ID = ""


class GitHubError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_now = time.monotonic


def client_id() -> str:
    raise NotImplementedError


async def start() -> dict:
    raise NotImplementedError


async def wait() -> dict:
    raise NotImplementedError


def status() -> dict:
    raise NotImplementedError


def token() -> str:
    raise NotImplementedError


def disconnect() -> None:
    raise NotImplementedError
