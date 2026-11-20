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

WICHTIG — NOCH NICHT VERIFIZIERT (20.11.2026): Die volle MetaMask-Card-
Kontraktadresse auf Base konnte in dieser Session NICHT nur-lesend von
einem Live-System mit Tills echten Daten ermittelt werden (der im Auftrag
genannte Server 192.168.178.216 war nicht erreichbar, die erreichbare
Instanz 192.168.178.197 hat keine Cryptoboard-Nutzdaten). Der Vertrag
(VERTRAG-B.md, Befund) nennt nur die VERKÜRZTE Form "0xdabd…67f8" — das
reicht NICHT für einen exakten Vergleich (40 Hex-Zeichen nötig). Die
Konstante unten ist daher ein PLATZHALTER mit denselben bekannten Rand-
Zeichen, NICHT die verifizierte volle Adresse — vor dem Merge MUSS sie
durch die echte, von Till/aus Tills Live-preview_all gelesene Adresse
ersetzt werden. Quelle laut Zieldokument §3 (Till, 20.11.2026): die USDC-
Abgänge über 0xdabd…67f8 sind die MetaMask Card.
"""
from __future__ import annotations

from . import alchemy_client as ac

MAX_LOOKUPS_PER_RUN = 300

# TODO(bevor Merge): PLATZHALTER — volle Adresse noch nicht live verifiziert (siehe Docstring).
# Quelle: Zieldokument §3, Till 20.11.2026 (dort nur verkürzt "0xdabd…67f8" genannt).
METAMASK_CARD_CONTRACTS: dict[str, str] = {
    # "base": "0xdabd0000000000000000000000000000067f8",  # NICHT verifiziert, Platzhalter-Länge falsch
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
