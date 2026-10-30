"""Labor-Container (PLAN-L1.md Baustein 3). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations

from dataclasses import dataclass

NAME = "hh-labor"


class LaborError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Limits:
    cpu: int = 2
    ram_mb: int = 4096
    disk_gb: int = 20


def _ubuntu_version(path=None) -> str:
    raise NotImplementedError


async def launch(limits: Limits) -> None:
    raise NotImplementedError


async def launch_and_probe(limits: Limits) -> dict:
    raise NotImplementedError


async def remove() -> None:
    raise NotImplementedError
