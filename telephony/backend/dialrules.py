"""Nummernregeln für ausgehende Anrufe (PLAN-ANRUFEN-3, Sicherheit Punkt 2).

``check`` gibt die gewählte Nummer als reine Ziffernfolge zurück (``+49`` → ``0``, ``+`` → ``00``) oder wirft
``Blocked(code)``:

- ``invalid``       – keine Telefonnummer (Buchstaben, ``*``/``#`` = FRITZ!Box-Steuercodes, zu kurz/lang)
- ``emergency``     – Notruf und Behördennummern (110, 112, 115, 116xxx) – nie, auch nicht mit Freigabe
- ``no_area_code``  – Ortsnummer ohne Vorwahl (sonst entscheidet die Ortsvorwahl der Anlage)
- ``premium``       – Mehrwert-/Sonderdienste, Auskunft, Satellit – nur mit Freigabe „Sondernummern“
- ``foreign``       – Ausland – nur mit Freigabe „Ausland“
"""
from __future__ import annotations

import re

_STRIP = re.compile(r"[ \-/().]")
_EMERGENCY = re.compile(r"^(?:0?11[02]|115|116\d{3})$")
_PREMIUM_DE = ("0900", "0137", "0138", "0180", "0181", "0190", "0118", "012", "032")
_PREMIUM_INTL = ("0088",)                 # Satellit und internationale Sondernetze (+881…, +882…, …)
MIN_DIGITS, MAX_DIGITS = 3, 20


class Blocked(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _digits(raw: str) -> str:
    text = (raw or "").strip()
    if ".." in text:
        raise Blocked("invalid")
    text = _STRIP.sub("", text)
    if text.startswith("+"):
        text = "00" + text[1:]
    if not text.isdigit() or not MIN_DIGITS <= len(text) <= MAX_DIGITS:
        raise Blocked("invalid")
    return text


def check(raw: str, *, allow_premium: bool = False, allow_foreign: bool = False) -> str:
    number = _digits(raw)
    if number.startswith("0049"):
        number = "0" + number[4:]
    if _EMERGENCY.match(number):
        raise Blocked("emergency")
    if number.startswith("118") or number.startswith(_PREMIUM_DE) or number.startswith(_PREMIUM_INTL):
        if not allow_premium:
            raise Blocked("premium")
        return number
    if number.startswith("00"):
        if not allow_foreign:
            raise Blocked("foreign")
        return number
    if not number.startswith("0"):
        raise Blocked("no_area_code")
    return number


def mask(number: str) -> str:
    """Wie eingehende Rufnummern: nur die letzten 3 Ziffern."""
    return "•••" + number[-3:] if len(number) >= 3 else "unbekannt"
