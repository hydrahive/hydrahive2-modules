"""Bündel in den Fork schieben (PLAN-L2.md Baustein 4). Platzhalter."""
from __future__ import annotations


class PushError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _remote_url(fork: str) -> str:
    raise NotImplementedError


def _base_url(target: str) -> str:
    raise NotImplementedError


async def _git(args, *, cwd, env, timeout=300):
    raise NotImplementedError


async def push_bundle(bundle, *, fork: str, target: str, branch: str, token: str, workdir) -> None:
    raise NotImplementedError
