"""Kleine, feste Incus-Schnittstelle für Hydra-Labor L1. Keine Shell."""
from __future__ import annotations

from hydrahive.containers import incus_client


def available() -> bool:
    return incus_client.is_available()


async def run(*args: str, timeout: float = 60.0, input_bytes: bytes | None = None) -> tuple[int, str, str]:
    return await incus_client._run(*args, timeout=timeout, input_bytes=input_bytes)


def first_column(csv_out: str) -> set[str]:
    """Namen aus `incus … list --format csv` (erste Spalte). incus 6.0.0 kennt bei network/acl/snapshot kein -c."""
    return {line.split(",", 1)[0].strip() for line in csv_out.splitlines() if line.strip()}
