"""Gemeinsame „buchbar“-Regel für On-Chain-Preview UND Commit.

Eine Quelle für beide Seiten, damit Vorschau (counts.buchbar, entry["buchbar"])
und Commit (skipped_details) nie auseinanderlaufen. Reine Funktion, kein Netz,
keine DB: Dedup kommt als Menge bereits vorhandener Hashes herein.
"""
from __future__ import annotations

import re
from typing import Any

from .validators import ID_RE, ISO_RE

HASH_RE = re.compile(r"^(base|ethereum):0x[0-9a-f]{64}:(sell|buy|transfer_out)$")
XCHAIN_HASH_RE = re.compile(r"^xchain:[0-9a-f]{64}:(base|ethereum):0x[0-9a-f]{64}:(sell|buy)$")


def _get(entry: Any, name: str) -> Any:
    return entry.get(name) if isinstance(entry, dict) else getattr(entry, name, None)


def hash_matches_kind(hash_: str | None, kind: str | None) -> bool:
    """Beide erlaubten Hash-Formate (base/ethereum:… und xchain:…), Suffix muss zum kind passen."""
    if not hash_ or not kind or not str(hash_).endswith(f":{kind}"):
        return False
    return bool(HASH_RE.match(hash_) or XCHAIN_HASH_RE.match(hash_))


def skip_reason(entry: Any, already: set[str] | frozenset[str] = frozenset()) -> str | None:
    """Warum ein Eintrag NICHT gebucht würde — None heißt buchbar.

    Gleiche Reihenfolge und Codes wie im Commit: hash_ungueltig, duplikat,
    coin_id_fehlt, preis_fehlt (nicht bei transfer_out), zeit_ungueltig.
    Funktioniert für Preview-Dicts und für die Pydantic-Modelle des Commits.
    """
    hash_, kind = _get(entry, "hash"), _get(entry, "kind")
    if not hash_matches_kind(hash_, kind):
        return "hash_ungueltig"
    if hash_ in already:
        return "duplikat"
    coin_id = _get(entry, "coin_id")
    if not coin_id or not ID_RE.match(str(coin_id).strip().lower()):
        return "coin_id_fehlt"
    # transfer_out ohne Preis ist kein Fehler (VERTRAG.md) — wird als 0 gebucht.
    if kind != "transfer_out" and _get(entry, "price") is None:
        return "preis_fehlt"
    executed_at = _get(entry, "executed_at")
    if not executed_at or not ISO_RE.match(str(executed_at).strip()):
        return "zeit_ungueltig"
    return None


def mark_bookable(entries: list[dict], already: set[str]) -> None:
    """Preview-Einträge: duplicate + buchbar (+ grund, falls nicht buchbar) setzen — dieselbe Regel wie der Commit."""
    for e in entries:
        e["duplicate"] = e["hash"] in already
        reason = skip_reason(e, already)
        e["buchbar"] = reason is None
        e["nicht_buchbar_grund"] = reason
