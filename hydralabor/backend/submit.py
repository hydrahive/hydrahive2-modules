"""Einreichen (PLAN-L2.md Baustein 4/5). Platzhalter."""
from __future__ import annotations

from .submit_box import SubmitError  # noqa: F401


def _workdir():
    raise NotImplementedError


def _stamp() -> str:
    raise NotImplementedError


def _versions() -> dict:
    raise NotImplementedError


async def submit(target: str, title: str, body: str, *, report) -> dict:
    raise NotImplementedError


async def suggest_target() -> str:
    raise NotImplementedError


async def refresh() -> None:
    raise NotImplementedError


def list_submissions() -> list[dict]:
    raise NotImplementedError
