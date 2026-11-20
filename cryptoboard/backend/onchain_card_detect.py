"""Erkennung von Kartenzahlungen unter den Ausgaben (Abgängen) — VERTRAG-B.md Punkt 2.

Eine Ausgabe (kind transfer_out) ist eine "kartenzahlung", wenn das Tx-Ziel
(eth_getTransactionByHash.to) auf den MetaMask-Card-Kontrakt zeigt, sonst
"abgang". Till bestätigt den Default im UI weiterhin NICHT automatisch
(Haken bleibt aus) — diese Datei liefert nur das Klassifikations-Merkmal.

eth_getTransactionByHash ist eine Allowlist-Methode (alchemy_client.
ALLOWED_METHODS) — ein Abruf je TX-Hash, im Prozess gecacht (Schlüssel
chain+tx_hash), damit ein zweiter preview_all-Lauf nicht erneut abruft.
Obergrenze MAX_LOOKUPS_PER_RUN pro Lauf: darüber hinaus art="abgang" +
art_unklar=True (nicht raten, Grenze sichtbar machen statt stillschweigend
falsch zu klassifizieren).

Kontrakt der MetaMask Card auf Base: 0xdabdafc43b2bc1c7d10c2bbce950a8cad4a367f8.
Quelle: Zieldokument §3 (Till, 20.11.2026: USDC-Abgänge über 0xdabd…67f8 sind die
MetaMask Card) und Live-Lesung am 20.11.2026 (eth_getTransactionByHash.to von 12/12
Stichproben aus Tills Base-USDC-Abgängen = diese Adresse).
"""
from __future__ import annotations

from . import alchemy_client as ac

MAX_LOOKUPS_PER_RUN = 300

# Quelle: Zieldokument §3 + Live-Lesung 20.11.2026 (siehe Docstring). Kleinschreibung, Vergleich case-insensitiv.
METAMASK_CARD_CONTRACTS: dict[str, str] = {
    "base": "0xdabdafc43b2bc1c7d10c2bbce950a8cad4a367f8",
}

_cache: dict[tuple[str, str], str | None] = {}


def clear_cache() -> None:
    """Für Tests — Prozess-Cache zwischen Läufen zurücksetzen."""
    _cache.clear()


async def _tx_to(chain: str, key: str, tx_hash: str) -> str | None:
    cache_key = (chain, tx_hash.lower())
    if cache_key in _cache:
        return _cache[cache_key]
    try:
        result = await ac.call(chain, key, "eth_getTransactionByHash", [tx_hash])
    except Exception:
        _cache[cache_key] = None
        return None
    to = result.get("to") if isinstance(result, dict) else None
    value = str(to).lower() if to else None
    _cache[cache_key] = value
    return value


async def classify_art(chain: str, key: str, tx_hash: str, *, lookups_used: int) -> tuple[str, bool, int]:
    """(art, art_unklar, lookups_used_neu) für eine Ausgabe.

    art ist "kartenzahlung" nur bei exaktem Treffer auf den Card-Kontrakt
    dieser Chain; sonst "abgang". art_unklar=True, wenn die Grenze erreicht
    ist ODER der Tx-to nicht ermittelt werden konnte (kein Raten — "abgang"
    bleibt der sichere Default, aber sichtbar als unklar markiert).
    """
    card_contract = METAMASK_CARD_CONTRACTS.get(chain)
    if card_contract is None:
        return "abgang", False, lookups_used
    if lookups_used >= MAX_LOOKUPS_PER_RUN:
        return "abgang", True, lookups_used
    to = await _tx_to(chain, key, tx_hash)
    lookups_used += 1
    if to is None:
        return "abgang", True, lookups_used
    art = "kartenzahlung" if to == card_contract.lower() else "abgang"
    return art, False, lookups_used
