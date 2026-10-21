"""Normbezeichnungen erkennen: „§ 536c BGB“, „BGB § 536c“, „Art. 3 GG“, „§ 536 Abs. 1 S. 2 BGB“ …

Grundlage für die exakte Suche (L1) und den Zitat-Prüfer (L4). Bezeichnung wie im Korpus (``enbez``):
„§ 536c“ bzw. „Art 3“ (gesetze-im-internet schreibt Artikel ohne Punkt).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    abbr: str
    enbez: str


_NUM = r"(\d+)\s*([a-zA-Z])?"
_TAIL = r"(?:\s+(?:Abs\.?|Absatz|S\.|Satz|Nr\.?|Nummer|Buchst\.?|lit\.?)\s*\d+[a-z]?)*"
_KIND = r"(§|Art\.?|Artikel)"


_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
          "XI": 11, "XII": 12, "XIII": 13, "XIV": 14}


def _sgb_book(raw: str) -> int | None:
    """„SGB II“ / „SGB 2“ → 2 (gesetze-im-internet schreibt arabisch, nur SGB X römisch)."""
    m = re.fullmatch(r"SGB\s+([IVX]+|\d+)", raw.strip(), re.IGNORECASE)
    if not m:
        return None
    part = m.group(1).upper()
    return int(part) if part.isdigit() else _ROMAN.get(part)


def _canon_abbr(raw: str, known: set[str]) -> str | None:
    want = re.sub(r"\s+", " ", raw.strip()).casefold()
    hit = next((k for k in known if k.casefold() == want), None)
    if hit:
        return hit
    book = _sgb_book(raw)
    if book is None:
        return None
    return next((k for k in known if _sgb_book(k) == book), None)


def _enbez(kind: str | None, num: str, letter: str | None) -> str:
    prefix = "Art" if kind and kind.startswith("Art") else "§"
    return f"{prefix} {num}{(letter or '').lower()}"


def parse_citation(raw: str, known_abbrs: set[str]) -> Citation | None:
    """Genau eine Norm aus ``raw`` (ganzer String). ``known_abbrs`` = Kürzel im Korpus (Groß/klein egal)."""
    s = re.sub(r"\s+", " ", (raw or "").strip())
    if not s:
        return None
    # „§ 536c BGB“ / „536c BGB“ / „Art. 3 GG“ / „§ 34 SGB X“ (Kürzel darf Leerzeichen/römische Zahl haben)
    m = re.fullmatch(rf"(?:{_KIND}\s*)?{_NUM}{_TAIL}\s+([A-Za-zÄÖÜäöü][\wÄÖÜäöü\- ]*?)", s)
    if m:
        abbr = _canon_abbr(m.group(4), known_abbrs)
        return Citation(abbr, _enbez(m.group(1), m.group(2), m.group(3))) if abbr else None
    # „BGB § 536c“
    m = re.fullmatch(rf"([A-Za-zÄÖÜäöü][\wÄÖÜäöü\- ]*?)\s+{_KIND}\s*{_NUM}{_TAIL}", s)
    if m:
        abbr = _canon_abbr(m.group(1), known_abbrs)
        return Citation(abbr, _enbez(m.group(2), m.group(3), m.group(4))) if abbr else None
    return None


# ── Normen in Fließtext (Plan L3 Schritt 1) ───────────────────────────────────

@dataclass(frozen=True)
class Finding:
    """Fundstelle im Text. ``citations`` = alle Normen der Stelle (bei „§§ 536, 536c BGB“ zwei); ``citation`` = die erste
    oder None, wenn das Gesetz nicht im Korpus ist (``unknown_law`` nennt dann das Kürzel)."""
    raw: str
    start: int
    end: int
    citations: tuple[Citation, ...]
    unknown_law: str | None = None

    @property
    def citation(self) -> Citation | None:
        return self.citations[0] if self.citations else None


_ONE = r"\d+\s?[a-zA-Z]?(?![\w])"
_PART = r"(?:\s*(?:Abs\.?|Absatz|S\.|Satz|Nr\.?|Nummer|Buchst\.?|lit\.?)\s*\d+[a-z]?)"
_ITEM = rf"{_ONE}{_PART}*(?:\s*ff?\.)?"
_SEP = r"\s*(?:,|und|bis|sowie|–|-)\s*"
# Kürzel: Großbuchstabe am Anfang, danach Buchstaben/Ziffern; SGB mit römischer/arabischer Buchnummer; „OWiG 1968“ nicht
_ABBR = r"(?:SGB\s+(?:[IVX]+|\d+)\b|[A-ZÄÖÜ][A-Za-zÄÖÜäöü]{1,14}\b)"
_FIND = re.compile(rf"(§§?|Art\.?|Artikel)\s*({_ITEM}(?:{_SEP}{_ITEM})*)\s+({_ABBR})")
_NUMS = re.compile(rf"(\d+)\s?([a-zA-Z])?(?![\w])(?:{_PART})*(?:\s*ff?\.)?")
_NOT_LAW = frozenset({"Abs", "Absatz", "Satz", "Nr", "Nummer", "und", "bis", "sowie", "ff"})


def find_all(text: str, known_abbrs: set[str]) -> list[Finding]:
    """Alle Normbezeichnungen in ``text`` mit Position. Nur Stellen mit „§“, „§§“ oder „Art.“ (keine nackten Zahlen)."""
    out: list[Finding] = []
    for m in _FIND.finditer(text or ""):
        kind, items, law = m.group(1), m.group(2), re.sub(r"\s+", " ", m.group(3))
        if law in _NOT_LAW:
            continue
        abbr = _canon_abbr(law, known_abbrs)
        raw = text[m.start():m.end()]
        if abbr is None:
            out.append(Finding(raw, m.start(), m.end(), (), unknown_law=law))
            continue
        cits = tuple(dict.fromkeys(Citation(abbr, _enbez(kind, n.group(1), n.group(2))) for n in _NUMS.finditer(items)))
        out.append(Finding(raw, m.start(), m.end(), cits))
    return out
