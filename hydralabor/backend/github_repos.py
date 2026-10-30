"""Forks beim Nutzer (PLAN-L2.md Baustein 2). Platzhalter."""
from __future__ import annotations

from . import github_api  # noqa: F401
from .github_api import GitHubError  # noqa: F401

TARGETS: dict[str, str] = {}


async def ensure_fork(token: str, login: str, target: str) -> str:
    raise NotImplementedError
