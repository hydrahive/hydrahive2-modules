"""L3: Probe bauen/starten/stoppen. Platzhalter."""
from __future__ import annotations


def _data_dir():
    raise NotImplementedError


async def build(report) -> None:
    raise NotImplementedError


async def start(report) -> None:
    raise NotImplementedError


async def stop(report) -> None:
    raise NotImplementedError


async def status() -> dict:
    raise NotImplementedError
