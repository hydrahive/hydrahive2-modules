"""Unterhaltungen (Spec §6): Wurzel aus References/In-Reply-To; ohne Bezug, aber mit Antwort-Präfix → über den Betreff.

Bewusst vorsichtig: Ein Betreff ohne Präfix („Rechnung“) fasst nichts zusammen, sonst landen fremde Mails in einem Faden.
"""
from __future__ import annotations

import re

_PREFIX = re.compile(r"^\s*((re|aw|wg|fw|fwd|antw|sv|vs|tr)\s*(\[\d+\])?\s*:\s*)+", re.IGNORECASE)


def normalize_subject(subject: str) -> str:
    return re.sub(r"\s+", " ", _PREFIX.sub("", subject or "")).strip().casefold()


def key(root: str, subject: str, message_id: str) -> str:
    if root:
        return root
    if _PREFIX.match(subject or "") and normalize_subject(subject):
        return "subj:" + normalize_subject(subject)[:200]
    return message_id or ""
