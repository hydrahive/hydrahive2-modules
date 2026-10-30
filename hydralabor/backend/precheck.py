"""Vorprüfung vor dem Einreichen (PLAN-L2.md Baustein 4): reine Regeln ohne Container – Ziel, geschützte Pfade,
Geheimnisse im Diff, Größe, Texte, Branchname. Was davon im Container gemessen wird (Diff, Tests), macht submit.py.
"""
from __future__ import annotations

import re
import unicodedata

MAX_FILES, MAX_LINES = 50, 3000
MAX_TITLE, MAX_BODY = 120, 4000

# Bereiche, die nur Till ändert – mit Grund.
PROTECTED = {
    "core": (
        (".github/", "Automatische Prüfungen des Projekts"),
        ("installer/", "Installation und Updates aller Server"),
        ("scripts/check_", "Prüfskripte"),
        ("LICENSE", "Lizenz"),
        ("SECURITY.md", "Sicherheitsrichtlinie"),
        ("docs/specs/", "Pläne – nur mit Tills Freigabe"),
    ),
    "modules": (
        (".github/", "Automatische Prüfungen des Projekts"),
        ("scripts/", "Prüfskripte des Modul-Repos"),
        ("hub.json", "Liste der Module im Modul-Hub"),
        ("LICENSE", "Lizenz"),
    ),
}


class PrecheckError(ValueError):
    pass


def guess_target(changed: dict[str, list[str]]) -> str:
    """`changed` = geänderte Dateien je Repo. Genau ein Repo geändert → das ist das Ziel, sonst kein Vorschlag."""
    hit = [k for k in ("core", "modules") if changed.get(k)]
    return hit[0] if len(hit) == 1 else ""


def protected(target: str, files: list[str]) -> list[str]:
    rules = PROTECTED[target]
    return [f for f in files if any(f.startswith(p) for p, _ in rules)]


def _patterns() -> list[re.Pattern[str]]:
    from hydrahive.credentials.redaction import SECRET_PATTERNS
    # Private Schlüssel gehen über mehrere Zeilen – schon die Kopfzeile reicht als Fund.
    return [*SECRET_PATTERNS, re.compile(r"gh[ousr]_[A-Za-z0-9]{30,}"), re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")]


def secrets(diff: str) -> list[str]:
    """Geheimnis-förmige Stellen in HINZUGEFÜGTEN Zeilen, als gekürzte Fundstelle (nie der volle Wert)."""
    added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    found: list[str] = []
    for pat in _patterns():
        for m in pat.finditer(added):
            found.append(m.group(0)[:6] + "…")
    return sorted(set(found))


def size_problem(files: int, lines: int) -> str:
    return "" if files <= MAX_FILES and lines <= MAX_LINES else "labor_submit_too_big"


def check_text(title: str, body: str) -> tuple[str, str]:
    t, b = (title or "").strip(), (body or "").strip()
    if not t or len(t) > MAX_TITLE or len(b) > MAX_BODY:
        raise PrecheckError("labor_submit_text_invalid")
    return t, b


_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def branch_name(title: str, stamp: str) -> str:
    s = unicodedata.normalize("NFKD", title.translate(_UMLAUT)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40].strip("-") or "aenderung"
    return f"labor/{s}-{stamp}"
