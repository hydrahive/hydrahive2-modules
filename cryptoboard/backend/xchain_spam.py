"""Spam-Erkennung für eingehende ERC20-Transfers — reine Funktion, kein Netz.

Regel (Till, 2026-11-20): ein eingehender ERC20-Transfer ist Spam, wenn
EINE der folgenden Bedingungen zutrifft (Grund in dieser Reihenfolge, der
erste zutreffende gewinnt):
  1. symbol_nicht_ascii   — Symbol passt NICHT auf ^[A-Za-z0-9]{1,15}$
                            (deckt Unicode-Fake-Zeichen wie "ꓴ឵ՏᎠ឵Ⲧ" ab,
                            die ein Symbol wie "USDT" nachbilden sollen)
  2. url_im_namen         — Symbol ODER Name enthält eine URL/Domain
                            (http://, https://, www., oder bekannte TLD
                            wie .com/.top/.xyz/… als Teilstring)
  3. unbekannter_token    — weder ein bekannter Kontrakt (chain_clients.
                            known_token) NOCH ein CoinGecko-Treffer
                            (resolve_coin_id-Ergebnis mit unresolved=True)

Garantie: Ein bekannter Kontrakt (z. B. echte USDC
0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 auf Base) ist NIE Spam — der
KONTRAKT entscheidet, nicht das mitgelieferte Symbol. Ein Fake-Token mit
Symbol "USDC" auf einem FREMDEN Kontrakt ist dagegen sehr wohl Spam-fähig
(Regel 3, falls auch CoinGecko ihn nicht kennt).

Die CoinGecko-Prüfung (Regel 3) braucht Netz — diese Funktion bekommt das
fertige Auflösungsergebnis (aus onchain_resolve.resolve_coin_id) bereits
übergeben, sie ruft selbst nie das Netz auf.
"""
from __future__ import annotations

import re

from . import chain_clients

_ASCII_SYMBOL_RE = re.compile(r"^[A-Za-z0-9]{1,15}$")
_URL_RE = re.compile(
    r"(https?://|www\.|\.(com|top|xyz|net|info|site|click|online|live|vip|app|biz|icu|cc|gq))",
    re.IGNORECASE,
)


def _is_known_contract(chain: str, contract: str | None) -> bool:
    if not contract:
        return False
    return chain_clients.known_token(chain, contract) is not None


def classify_incoming(chain: str, contract: str | None, symbol: str, name: str, *,
                       resolved: bool) -> str | None:
    """Liefert den Spam-Grund oder None (kein Spam). `resolved` kommt aus
    onchain_resolve.resolve_coin_id (unresolved invertiert) — echter
    Kontrakt-Treffer (known_token) übersteuert IMMER, egal was `resolved` sagt."""
    if _is_known_contract(chain, contract):
        return None
    if not _ASCII_SYMBOL_RE.match(symbol or ""):
        return "symbol_nicht_ascii"
    if _URL_RE.search(symbol or "") or _URL_RE.search(name or ""):
        return "url_im_namen"
    if not resolved:
        return "unbekannter_token"
    return None


def is_spam(chain: str, contract: str | None, symbol: str, name: str, *, resolved: bool) -> bool:
    return classify_incoming(chain, contract, symbol, name, resolved=resolved) is not None
