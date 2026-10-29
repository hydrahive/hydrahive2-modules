"""Sender und Apps aus freier Eingabe finden („ZDF“, „Platz 7“, „kabel 1“, „ard“). Bei Zweifel nicht raten.

Reihenfolge: Platznummer → genauer Name → Name ohne Zusatz („HD“) → eindeutiger Anfang. Mehrere gleich gute Treffer
ergeben tv_channel_ambiguous mit den Kandidaten, damit der Agent nachfragt.
"""
from __future__ import annotations

import re

from .client_errors import TVError

_ALIASES = {"ard": "das erste", "erstes": "das erste", "1live": "einslive", "pro7": "prosieben",
            "pro 7": "prosieben", "rtl2": "rtlzwei", "rtl 2": "rtlzwei", "kabel1": "kabeleins"}
_NUMBER_WORDS = {"eins": "1", "zwei": "2", "drei": "3", "vier": "4", "fünf": "5", "sechs": "6", "sieben": "7",
                 "acht": "8", "neun": "9", "zehn": "10"}


def _norm(text: str) -> str:
    t = (text or "").lower().strip()
    t = _ALIASES.get(t, t)
    t = re.sub(r"[^a-z0-9äöüß]+", "", t)
    for word, digit in _NUMBER_WORDS.items():
        t = t.replace(word, digit)
    return _ALIASES.get(t, t)


def _base(name: str) -> str:
    return re.sub(r"(hd|uhd|sd)$", "", _norm(name))


def pick_channel(channels: list[dict], query: str) -> dict:
    q = (query or "").strip().lower()
    if not q:
        raise TVError("tv_channel_unknown", "Kein Sender angegeben.")
    m = re.fullmatch(r"(?:platz|programm|kanal|nr\.?|nummer)?\s*(\d{1,4})", q)
    if m:
        hit = [c for c in channels if c["number"] == int(m.group(1))]
        if hit:
            return hit[0]
        raise TVError("tv_channel_unknown", f"Kein Sender auf Platz {m.group(1)}.")
    nq = _norm(q)
    for key in (_norm, _base):
        hits = [c for c in channels if key(c["name"]) == nq or key(c["name"]) == _base(q)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            hits.sort(key=lambda c: c["number"])
            return hits[0]
    starts = [c for c in channels if _norm(c["name"]).startswith(nq) and len(nq) >= 3]
    if len(starts) == 1:
        return starts[0]
    if len(starts) > 1:
        names = ", ".join(c["name"] for c in starts[:6])
        raise TVError("tv_channel_ambiguous", f"Mehrere Sender passen: {names}.")
    raise TVError("tv_channel_unknown", f"Sender „{query.strip()[:40]}“ nicht gefunden.")


def pick_app(apps: list[dict], name: str) -> dict:
    q = _norm(name)
    if not q:
        raise TVError("tv_app_unknown", "Keine App angegeben.")
    exact = [a for a in apps if _norm(a["name"]) == q]
    if exact:
        return exact[0]
    starts = [a for a in apps if _norm(a["name"]).startswith(q)]
    if len(starts) == 1:
        return starts[0]
    raise TVError("tv_app_unknown", f"App „{(name or '').strip()[:40]}“ nicht gefunden.")
