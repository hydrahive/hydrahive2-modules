"""Eigenes Netz + ACL für das Hydra-Labor (PLAN-L1.md). Platzhalter – Umsetzung im nächsten Commit."""
from __future__ import annotations

from dataclasses import dataclass

NET = "hhlabor0"
ACL = "hhlabor-acl"


class LaborNetworkError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class NetworkState:
    name: str
    acl: str
    subnet: str


def _host_networks() -> set[str]:
    return set()


def _host_addresses() -> set[str]:
    return set()


def choose_subnet() -> str:
    raise NotImplementedError


async def ensure_network() -> NetworkState:
    raise NotImplementedError


def probe_targets(gateway: str) -> list[str]:
    raise NotImplementedError


async def probe(container: str, gateway: str) -> dict:
    raise NotImplementedError
