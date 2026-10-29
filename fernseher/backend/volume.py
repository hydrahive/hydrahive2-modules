"""Lautstärke-Ziel aus freier Eingabe („20“, „+3“, „-5“) – ohne Netz, gut zu testen."""
from __future__ import annotations

from .client_errors import TVError

MAX_STEP = 20


def target(value: str, current: int) -> int:
    """Zielwert aus „20“, „+3“ oder „-5“. Unter 0 wird 0, über 100 wird 100."""
    v = (value or "").strip()
    sign = v[:1] if v[:1] in "+-" else ""
    digits = v[1:] if sign else v
    if not digits.isdigit():
        raise TVError("tv_volume_invalid", "Lautstärke als Zahl 0–100 oder +n/-n angeben.")
    n = int(digits)
    if sign == "+":
        return min(100, current + n)
    if sign == "-":
        return max(0, current - n)
    return min(100, n)
