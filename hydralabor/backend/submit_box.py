"""Einreichen – Teil im Container (PLAN-L2.md Baustein 4). Platzhalter."""
from __future__ import annotations

REPO: dict[str, str] = {}
MAX_BUNDLE = 50 * 1024 * 1024


class SubmitError(RuntimeError):
    def __init__(self, code: str, detail: object = None):
        super().__init__(code)
        self.code = code
        self.detail = detail


async def changes(target: str) -> dict:
    raise NotImplementedError


async def commit(target: str, title: str, login: str, uid: int) -> None:
    raise NotImplementedError


async def diff(target: str) -> str:
    raise NotImplementedError


async def run_tests(target: str, files: list[str]) -> dict:
    raise NotImplementedError


async def bundle(target: str, workdir):
    raise NotImplementedError
