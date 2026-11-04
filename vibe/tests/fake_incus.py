"""Kleines incus im Speicher für die Tests (Netze, ACLs, Container, exec).

Baustein 1 braucht nur `available`/`run`; die Container- und Netz-Nachbildung wächst mit Baustein 2.
"""
from __future__ import annotations


class FakeIncus:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.fail: dict[str, str] = {}          # Teiltext eines Aufrufs → Fehlertext

    async def run(self, *args: str, timeout: float = 60.0, input_bytes: bytes | None = None) -> tuple[int, str, str]:
        a = list(args)
        self.calls.append(a)
        line = " ".join(a)
        for part, err in self.fail.items():
            if part in line:
                return 1, "", err
        return 0, "", ""
