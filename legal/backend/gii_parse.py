"""XML von gesetze-im-internet.de (gii-norm.dtd 1.01) → Gesetz mit Normen. Nur Standardbibliothek.

Befunde aus L0 (legal/SPEC-LEGAL.md §6a):
- Zitierkürzel steht in ``amtabk`` (OWiG), ``jurabk`` ist teils „OWiG 1968“.
- Gliederungseinheiten (Abschnitt, Titel …) sind eigene ``<norm>`` ohne ``enbez``; ihr Titel gilt für die folgenden
  Normen – 815 Normen haben keine eigene Überschrift, die Gliederung trägt dort die Suche.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

_SKIP_ENBEZ = {"Inhaltsübersicht", "Inhaltsverzeichnis", "Eingangsformel", "Schlussformel"}
_REPEALED = re.compile(r"^\(?\s*(weggefallen|aufgehoben)\s*\)?\.?$", re.IGNORECASE)
_EMPTY = re.compile(r"^[\s\-–—.]*$")          # Text nur „-“ (z. B. JGG § 19): kein Inhalt
_BREAK_BEFORE = {"P", "DT", "BR", "Title", "Subtitle"}


class GiiParseError(ValueError):
    pass


@dataclass(frozen=True)
class Norm:
    abbr: str
    enbez: str
    doknr: str
    title: str
    gliederung: str
    text: str
    position: int


@dataclass
class Law:
    key: str
    abbr: str
    title: str
    stand: str
    norms: list[Norm] = field(default_factory=list)


def _text_of(el: ET.Element | None) -> str:
    """Absätze und Listenpunkte je eine Zeile; Fußnoten bleiben draußen; Leerraum zusammengefasst."""
    if el is None:
        return ""
    parts: list[str] = []

    def walk(e: ET.Element) -> None:
        if e.tag in ("Footnotes", "Footnote", "FnR"):
            if e.tail:
                parts.append(e.tail)
            return
        if e.tag in _BREAK_BEFORE:
            parts.append("\n")
        if e.tag == "DD":
            parts.append(" ")
        if e.text:
            parts.append(e.text)
        for child in e:
            walk(child)
        if e.tail:
            parts.append(e.tail)

    walk(el)
    lines = (re.sub(r"\s+", " ", line).strip() for line in "".join(parts).split("\n"))
    return "\n".join(line for line in lines if line)


def _stand(md: ET.Element) -> str:
    return " ".join(
        (s.findtext("standkommentar") or "").strip()
        for s in md.findall("standangabe") if (s.findtext("standkommentar") or "").strip()
    )


def parse_law(key: str, xml: bytes) -> Law:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise GiiParseError(f"XML nicht lesbar ({key}): {e}") from None
    norms_el = root.findall("norm")
    head = next((n.find("metadaten") for n in norms_el
                 if n.find("metadaten/langue") is not None or n.find("metadaten/amtabk") is not None), None)
    if head is None:
        raise GiiParseError(f"Kein Gesetz-Kopf gefunden ({key})")
    abbr = (head.findtext("amtabk") or head.findtext("jurabk") or key.upper()).strip()
    law = Law(key=key, abbr=abbr, title=(head.findtext("langue") or abbr).strip(), stand=_stand(head))

    gliederung = ""
    for el in norms_el:
        md = el.find("metadaten")
        if md is None:
            continue
        enbez = (md.findtext("enbez") or "").strip()
        unit = md.find("gliederungseinheit")
        if not enbez:
            if unit is not None:
                bez = (unit.findtext("gliederungsbez") or "").strip()
                titel = (unit.findtext("gliederungstitel") or "").strip()
                gliederung = f"{bez} {titel}".strip()
            continue
        if enbez in _SKIP_ENBEZ:
            continue
        title = re.sub(r"\s+", " ", "".join(md.find("titel").itertext()) if md.find("titel") is not None else "").strip()
        text = _text_of(el.find("textdaten/text/Content"))
        if _REPEALED.match(title) or _EMPTY.match(text) or _REPEALED.match(text):
            continue
        law.norms.append(Norm(abbr=abbr, enbez=enbez, doknr=el.get("doknr", ""), title=title,
                              gliederung=gliederung, text=text, position=len(law.norms)))
    return law
