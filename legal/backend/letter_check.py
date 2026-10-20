"""Prüfliste für Briefe ohne KI (Plan L3 Schritt 2, Spec §4.7). Nichts blockiert – die Liste zeigt, was fehlt.

Punkte: Absender und Empfänger (Name + Anschrift), Datum, Betreff, Aktenzeichen (falls der Fall eins hat), Frist als
Datum, Frist nicht vor dem Briefdatum, Normen belegt (Korpus), Zustellweg, Anlagenliste.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from . import corpus_store
from .citation import find_all
from .norm_view import citation_text

DELIVERY = ("einwurf_einschreiben", "einschreiben_rueckschein", "bote", "fax", "mail", "brief", "persoenlich")
_DATE_DE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_RELATIVE = re.compile(
    r"\b(?:binnen|innerhalb(?:\s+von)?|in)\s+(?:\d+|einer|eines|einem|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|"
    r"vierzehn|zwanzig|dreißig)\s+(?:Werk)?(?:Tag|Tage|Tagen|Woche|Wochen|Monat|Monats|Monaten)\b", re.IGNORECASE)
_BOUNDARY = re.compile(r"[.!?](?=\s+[A-ZÄÖÜ])")
_ATTACH = re.compile(r"\bAnlage[n]?\b", re.IGNORECASE)


def _s(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def _lines(v: Any) -> list[str]:
    return [line for line in (ln.strip() for ln in _s(v).splitlines()) if line]


def _iso(v: Any) -> date | None:
    try:
        return date.fromisoformat(_s(v))
    except ValueError:
        return None


def _de_dates(text: str) -> list[date]:
    out = []
    for d, m, y in _DATE_DE.findall(text):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    return out


_REF_PREFIX = re.compile(r"^(?:Az\.?|Aktenzeichen|Ihr(?:e)?\s+Zeichen|Zeichen|Gz\.?|Geschäftszeichen)[:\s]*", re.IGNORECASE)


def _ref_norm(text: str) -> str:
    """Leerzeichen um / - . innerhalb von Aktenzeichen weg („12 / 345“ = „12/345“), sonst einfache Leerzeichen."""
    return re.sub(r"\s*([/\-])\s*", r"\1", re.sub(r"\s+", " ", text)).strip()


def _ref_in(ref: str, text: str) -> bool:
    """Aktenzeichen ohne „Az.“ muss als eigenes Stück im Text stehen. Datum- oder Zahlteile („1“ in „1. OG“, „2026“ in
    „20.10.2026“) zählen nicht: links/rechts kein Buchstabe, keine Ziffer und kein . / -"""
    core = _ref_norm(_REF_PREFIX.sub("", ref.strip()))
    if not core:
        return True
    # rechts kein Wortzeichen, kein / -, kein „.Ziffer“ (Datum) und keine Ordnungszahl „1. OG“ (Punkt + Leerzeichen + Wort);
    # ein Satzende-Punkt („… 12/345.“ am Textende oder vor Zeilenende) zählt als Ende.
    after = r"(?![\w/\-]|\.\w|\.\s+[\wÄÖÜäöü])"
    return re.search(r"(?<![\w./\-])" + re.escape(core) + after, _ref_norm(text)) is not None


def _item(key: str, ok: bool, hint: str = "") -> dict[str, Any]:
    return {"key": key, "ok": bool(ok), "hint": "" if ok else hint}


def _address(key: str, who: str, v: Any) -> dict[str, Any]:
    lines = _lines(v)
    if not lines:
        return _item(key, False, f"{who} fehlt (Name und Anschrift).")
    if len(lines) < 2 or not any(re.search(r"\d", ln) for ln in lines[1:]):
        return _item(key, False, f"{who}: Anschrift fehlt (Straße und PLZ/Ort, je eine Zeile).")
    return _item(key, True)


def _deadline_items(body: str, letter_date: date, today: date) -> list[dict[str, Any]]:
    # Datum im selben Satz zählt. Satzgrenze = Zeilenumbruch oder [.!?] + Leerzeichen + Großbuchstabe (nicht der Punkt im
    # Datum „03.11.2026“ oder in „Abs.“). Einfacher und robuster: Umkreis bis zur nächsten Satzgrenze links/rechts.
    missing = []
    for m in _RELATIVE.finditer(body):
        left = max(body.rfind("\n", 0, m.start()), *(i.end() - 1 for i in _BOUNDARY.finditer(body, 0, m.start())), -1)
        nxt = _BOUNDARY.search(body, m.end())
        right = min(x for x in (body.find("\n", m.end()), nxt.start() + 1 if nxt else -1, len(body)) if x >= 0)
        if not _de_dates(body[left + 1:right]):
            missing.append(m.group(0))
    date_item = _item("deadline_date", not missing,
                      f"Frist „{missing[0]}“ ohne Datum – bitte das Enddatum nennen (z. B. „bis zum 10.11.2026“)."
                      if missing else "")
    ref = max(letter_date, today) if letter_date else today
    past = [d for d in _de_dates(body) if re.search(r"bis\s+(?:zum\s+)?" + re.escape(d.strftime("%d.%m.%Y")), body)
            or re.search(r"bis\s+(?:zum\s+)?" + re.escape(f"{d.day}.{d.month}.{d.year}"), body)]
    late = [d for d in past if d < ref]
    future_item = _item("deadline_future", not late,
                        f"Frist {late[0].strftime('%d.%m.%Y')} liegt vor dem Briefdatum bzw. heute." if late else "")
    return [date_item, future_item]


def _norms(body: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    known = corpus_store.known_abbrs()
    norms: list[dict[str, Any]] = []
    for f in find_all(body, known):
        if f.unknown_law:
            norms.append({"raw": f.raw, "citation": f.raw, "found": False})
            continue
        for c in f.citations:
            found = corpus_store.get_norm(c.abbr, c.enbez) is not None
            norms.append({"raw": f.raw if len(f.citations) == 1 else citation_text(c.abbr, c.enbez),
                          "citation": citation_text(c.abbr, c.enbez), "found": found})
    bad = [n["citation"] for n in norms if not n["found"]]
    if not norms:
        item = _item("norms", False, "Im Brief steht keine Norm – auf welche Vorschrift stützt sich das Schreiben?")
    else:
        item = _item("norms", not bad, f"Nicht im Gesetzeskorpus gefunden: {', '.join(bad)} – bitte prüfen.")
    return norms, item


def check(letter: dict[str, Any], *, case: dict[str, Any] | None = None, today: date | None = None) -> dict[str, Any]:
    letter = letter if isinstance(letter, dict) else {}
    today = today or date.today()
    body = _s(letter.get("body"))
    letter_date = _iso(letter.get("date"))
    items = [
        _address("sender", "Absender", letter.get("sender")),
        _address("recipient", "Empfänger", letter.get("recipient")),
        _item("date", letter_date is not None, "Datum fehlt oder ist ungültig."),
        _item("subject", bool(_s(letter.get("subject"))), "Betreff fehlt."),
    ]
    their_ref = _s((case or {}).get("their_ref"))
    has_ref = not their_ref or _ref_in(their_ref, _s(letter.get("their_ref")) + " | " + _s(letter.get("subject")))
    items.append(_item("reference", has_ref, f"Aktenzeichen der Gegenseite „{their_ref}“ angeben (Bezugszeichen)."))
    items.extend(_deadline_items(body, letter_date, today))
    norms, norm_item = _norms(body)
    items.append(norm_item)
    items.append(_item("delivery", _s(letter.get("delivery")) in DELIVERY,
                       "Zustellweg festlegen – zum Nachweis am besten Einwurf-Einschreiben oder Bote."))
    att = letter.get("attachments") if isinstance(letter.get("attachments"), list) else []
    att = [a for a in att if _s(a)]
    items.append(_item("attachments", bool(att) or not _ATTACH.search(body),
                       "Im Text ist von Anlagen die Rede, aber die Anlagenliste ist leer."))
    return {"items": items, "norms": norms, "ok": all(i["ok"] for i in items)}
