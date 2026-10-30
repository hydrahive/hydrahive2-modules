"""Voraussetzungen (Assistent Schritt 1). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations


def _mem_available_mb(path=None):
    raise NotImplementedError


def _core_has_k1() -> bool:
    raise NotImplementedError


async def _incus_version() -> str:
    raise NotImplementedError


async def _pool_free_gb():
    raise NotImplementedError


async def run(*, disk_gb: int, ram_mb: int) -> dict:
    raise NotImplementedError
