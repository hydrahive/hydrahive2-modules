"""Empfänger prüfen (PLAN-M2 Schritt 1, Spec §11). Nie rohe Eingaben in Kopfzeilen: jede Adresse wird zerlegt,
geprüft und neu geschrieben. CR/LF/NUL irgendwo → Fehler (Kopfzeilen-Injektion). Bcc kommt nie in den Kopf (compose).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from email.headerregistry import Address
from email.utils import formataddr, getaddresses

from . import providers

MAX_RECIPIENTS = 100
_BAD = re.compile(r"[\r\n\x00]")


class AddressError(ValueError):
    pass


@dataclass(frozen=True)
class Recipient:
    name: str
    addr: str


def _split(text: str) -> list[str]:
    """Am Komma/Semikolon trennen, aber nicht innerhalb von Anführungszeichen oder <…>."""
    out, buf, quote, angle = [], [], False, False
    for ch in text:
        if ch == '"' and not angle:
            quote = not quote
        elif ch == "<" and not quote:
            angle = True
        elif ch == ">" and not quote:
            angle = False
        if ch in ",;" and not quote and not angle:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def _one(part: str) -> Recipient:
    # Erste Schicht: Klammern grob; zweite Schicht: getaddresses + Adressprüfung lehnen dieselben Fälle ab (getestet).
    if part.count("<") > 1 or part.count(">") > 1 or ("<" in part) != (">" in part):
        raise AddressError(f"ungültige Adresse: {part[:80]}")
    pairs = getaddresses([part])
    if len(pairs) != 1:
        raise AddressError(f"ungültige Adresse: {part[:80]}")
    name, addr = pairs[0]
    if not addr or "<" in part and not part.rstrip().endswith(">"):
        raise AddressError(f"ungültige Adresse: {part[:80]}")
    try:
        providers.domain(addr)
    except ValueError:
        raise AddressError(f"ungültige Adresse: {part[:80]}") from None
    return Recipient(name=name.strip()[:200], addr=addr.strip())


def parse_list(text: str) -> list[Recipient]:
    if not isinstance(text, str):
        raise AddressError("Empfänger müssen Text sein")
    if _BAD.search(text):
        raise AddressError("Zeilenumbruch oder Nullzeichen in Empfängern")
    seen, out = set(), []
    for part in _split(text):
        r = _one(part)
        if r.addr.lower() not in seen:
            seen.add(r.addr.lower())
            out.append(r)
    if len(out) > MAX_RECIPIENTS:
        raise AddressError(f"höchstens {MAX_RECIPIENTS} Empfänger")
    return out


def header(recipients: list[Recipient]) -> str:
    """Kopfzeilen-Wert: Namen nach RFC 2047 (formataddr), Adressen roh; nie ein Zeilenumbruch."""
    parts = []
    for r in recipients:
        user, _, domain = r.addr.rpartition("@")
        Address(username=user, domain=domain)          # wirft bei unzulässigen Zeichen
        parts.append(formataddr((r.name, r.addr), charset="utf-8") if r.name else r.addr)
    out = ", ".join(parts)
    if _BAD.search(out):
        raise AddressError("Kopfzeile ungültig")
    return out


def without(recipients: list[Recipient], own: str) -> list[Recipient]:
    return [r for r in recipients if r.addr.lower() != (own or "").lower()]
