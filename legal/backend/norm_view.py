"""Norm für Oberfläche und Werkzeug aufbereiten: Zitierform, amtlicher Link, Stand (Spec §4.1, §4.5)."""
from __future__ import annotations

import re
from datetime import UTC, datetime

from . import corpus_store as store
from .citation import parse_citation

BASE = "https://www.gesetze-im-internet.de"


class NormError(ValueError):
    """``code``: invalid | unknown_law | not_found | bad_date"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def official_url(law_key: str, enbez: str) -> str:
    """„§ 536c“ → …/bgb/__536c.html, „Art 3“ → …/gg/art_3.html (geprüft 20.10.2026, HTTP 200)."""
    m = re.fullmatch(r"(§|Art)\s+(\w+)", enbez)
    if not m:
        return f"{BASE}/{law_key}/"
    return f"{BASE}/{law_key}/{'__' if m.group(1) == '§' else 'art_'}{m.group(2)}.html"


def citation_text(abbr: str, enbez: str) -> str:
    return f"{enbez.replace('Art ', 'Art. ')} {abbr}"


def _as_of(raw: str | None) -> str | None:
    """„2026-10-25“ → Ende dieses Tages (UTC); Zeitpunkt mit Zeitzone wird nach UTC umgerechnet."""
    if not raw:
        return None
    try:
        d = datetime.fromisoformat(raw)
    except ValueError:
        raise NormError("bad_date", f"Datum nicht lesbar: {raw!r} (erwartet z. B. 2026-10-25)") from None
    if "T" not in raw:
        return d.strftime("%Y-%m-%dT23:59:59Z")
    if d.tzinfo is not None:
        d = d.astimezone(UTC)
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def lookup(citation: str, *, as_of: str | None = None) -> dict:
    known = store.known_abbrs()
    cit = parse_citation(citation, known)
    if cit is None:
        abbr = re.findall(r"[A-Za-zÄÖÜäöü][\wÄÖÜäöü]*", citation or "")
        if abbr and re.search(r"\d", citation or "") and not any(a in known for a in abbr):
            raise NormError("unknown_law", f"Gesetz {abbr[-1]!r} ist nicht im Korpus (Recht → Gesetze → nachladen).")
        raise NormError("invalid", f"Keine Normbezeichnung erkannt: {citation!r} (z. B. „§ 536c BGB“).")
    n = store.get_norm(cit.abbr, cit.enbez, as_of=_as_of(as_of))
    if n is None:
        raise NormError("not_found", f"{citation_text(cit.abbr, cit.enbez)} ist nicht im Korpus"
                        + (" (zu diesem Datum)." if as_of else "."))
    law = store.get_law(n["law_key"]) or {}
    return {
        "citation": citation_text(n["abbr"], n["enbez"]),
        "abbr": n["abbr"], "enbez": n["enbez"], "title": n["title"], "gliederung": n["gliederung"],
        "text": n["text"], "law_title": law.get("title", ""), "stand": law.get("stand", ""),
        "fetched_at": n["valid_from"], "valid_to": n["valid_to"],
        "url": official_url(n["law_key"], n["enbez"]),
    }
