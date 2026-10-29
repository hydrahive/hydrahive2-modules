"""Fehler des Fernseher-Moduls mit festem Code (err.<code> in de/en)."""
from __future__ import annotations


class TVError(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
