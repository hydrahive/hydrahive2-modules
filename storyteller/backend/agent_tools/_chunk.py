"""Lange Szenen in Abschnitten an Agenten geben (Task 29fb3911).

Ein Abschnitt endet bevorzugt an einer Absatzgrenze, sonst nach einem Leerzeichen, nur notfalls hart.
Die Abschnitte ergeben zusammengesetzt genau den Szenentext – es geht nichts verloren und nichts doppelt.
"""
from __future__ import annotations

_SPACE = (" ", "\n", "\t")


def chunk(text: str, offset: int, size: int) -> tuple[str, int | None]:
    """(Abschnitt ab ``offset``, Beginn des nächsten Abschnitts oder None am Ende)."""
    end = offset + size
    if end >= len(text):
        return text[offset:], None
    window = text[offset:end]
    cut = window.rfind("\n\n")
    if cut >= size // 2:
        cut += 2
    else:
        cut = max(window.rfind(c) for c in _SPACE) + 1
        if cut <= 0:
            cut = size
    return window[:cut], offset + cut
