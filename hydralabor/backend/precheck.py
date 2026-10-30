"""Vorprüfung vor dem Einreichen (PLAN-L2.md Baustein 4). Platzhalter."""
from __future__ import annotations


class PrecheckError(ValueError):
    pass


def guess_target(changed: dict) -> str:
    raise NotImplementedError


def protected(target: str, files: list[str]) -> list[str]:
    raise NotImplementedError


def secrets(diff: str) -> list[str]:
    raise NotImplementedError


def size_problem(files: int, lines: int) -> str:
    raise NotImplementedError


def check_text(title: str, body: str) -> tuple[str, str]:
    raise NotImplementedError


def branch_name(title: str, stamp: str) -> str:
    raise NotImplementedError
