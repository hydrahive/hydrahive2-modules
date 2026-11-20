"""MT940 Feld :86: mit ?-Subfeldern zerlegen (deutscher DK-/Sparkassen-Standard).

Feldschlüssel laut Formatbeschreibung (kontopruef.de/mt940s.shtml, Kreissparkasse
Köln „Formatbeschreibung MT 940“): 00 Buchungstext, 10 Primanota, 20–29 und 60–63
Verwendungszweck, 30 BLZ/BIC, 31 Kontonummer/IBAN, 32–33 Name, 34
Textschlüsselergänzung. Die ersten drei Ziffern sind der Geschäftsvorfallcode.

Im Verwendungszweck stecken SEPA-Kennungen (EREF+, MREF+, CRED+, SVWZ+, ABWA+ …).
Zeilenumbrüche der Bank (alle 27/65 Zeichen) werden vor dem Zerlegen entfernt,
weil sie mitten im Wort liegen („Abrech\\nnung“).
Ohne ?-Subfelder liefert parse() None – dann gilt der alte Leerzeichen-Weg.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SUB = re.compile(r"\?(\d{2})")
_SEPA_KEYS = ("EREF", "KREF", "MREF", "CRED", "DEBT", "SVWZ", "ABWA", "ABWE", "IBAN", "BIC", "COAM", "OAMT")
_SEPA = re.compile(r"(?<![A-Z])(" + "|".join(_SEPA_KEYS) + r")\s?\+")


@dataclass(frozen=True)
class Detail86:
    booking_text: str | None
    purpose: str | None
    counterparty: str | None
    counterparty_iban: str | None
    reference: str | None


def _clean(value: str | None) -> str | None:
    text = " ".join((value or "").split())
    return text or None


def _subfields(raw: str) -> dict[str, list[str]]:
    text = raw.replace("\r", "").replace("\n", "")
    parts = _SUB.split(text)
    out: dict[str, list[str]] = {}
    for i in range(1, len(parts) - 1, 2):
        out.setdefault(parts[i], []).append(parts[i + 1])
    return out


def _sepa(purpose_raw: str) -> dict[str, str]:
    found: dict[str, str] = {}
    matches = list(_SEPA.finditer(purpose_raw))
    for n, m in enumerate(matches):
        end = matches[n + 1].start() if n + 1 < len(matches) else len(purpose_raw)
        found.setdefault(m.group(1), purpose_raw[m.end():end].strip())
    return found


def parse(raw: str) -> Detail86 | None:
    """Subfelder auswerten; None, wenn das Feld keine ?-Struktur hat."""
    if not _SUB.search(raw or ""):
        return None
    sub = _subfields(raw)
    purpose_raw = "".join("".join(sub.get(f"{k:02d}", [])) for k in (*range(20, 30), *range(60, 64)))
    sepa = _sepa(purpose_raw)
    if sepa:
        purpose = sepa.get("SVWZ")
    else:
        purpose = purpose_raw
    name = "".join("".join(sub.get(k, [])) for k in ("32", "33"))
    return Detail86(
        booking_text=_clean("".join(sub.get("00", []))),
        purpose=_clean(purpose),
        counterparty=_clean(name) or _clean(sepa.get("ABWA")),
        counterparty_iban=_clean("".join(sub.get("31", []))) or _clean(sepa.get("IBAN")),
        reference=_clean(sepa.get("EREF")),
    )
