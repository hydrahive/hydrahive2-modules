"""Adress-Validierung je Chain — reine Regex-Prüfung, keine I/O.

Adressen fließen in Block-Explorer-URLs/RPC-Calls; daher VOR jedem Upstream-Call
strikt validieren (kein Pfad-/Param-Schmuggel). Eine zentrale Quelle für Routen
und Aggregation.
"""
from __future__ import annotations

import re

CHAINS = ("base", "tron", "bitcoin")

# EVM (Base): 0x + 40 Hex
_EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
# Tron: T + 33 Base58
_TRON_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
# Bitcoin: bech32 (bc1…) oder Base58 (1…/3…)
_BTC_RE = re.compile(r"^(bc1[a-z0-9]{20,80}|[13][a-km-zA-HJ-NP-Z1-9]{25,39})$")

_VALIDATORS = {
    "base": _EVM_RE,
    "tron": _TRON_RE,
    "bitcoin": _BTC_RE,
}


def is_valid_chain(chain: str) -> bool:
    return chain in CHAINS


def is_valid_address(chain: str, address: str) -> bool:
    rx = _VALIDATORS.get(chain)
    if rx is None:
        return False
    return bool(rx.match(address.strip()))
