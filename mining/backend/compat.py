"""Verträglichkeit mit älteren Rechner-Clients.

Der Client prüft jeden Auftrag gegen seinen eingebauten Katalog und lehnt
unbekannte Coins ab (``job_rejected:unknown_coin``). Der Server darf älteren
Clients deshalb nur Coins zuteilen, die deren Katalog kennt.

Neue Coins im Katalog → hier mit der ersten Client-Version eintragen, die sie kennt.
"""
from __future__ import annotations

import re

from . import catalog

# Coin → erste Client-Version, die ihn kennt. Fehlt ein Coin: seit jeher bekannt.
COIN_SINCE: dict[str, tuple[int, ...]] = {
    c: (0, 4, 0) for c in ("alph", "etc", "ethw", "octa", "qtc", "xtm-c29", "xtm-sha3x")
}
_VER_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?")
_OLDEST = (0, 0, 0)


def parse(version: str | None) -> tuple[int, ...]:
    """'0.3.1' → (0, 3, 1). Unbekannt/kaputt → älteste Version (sicher: nur alte Coins)."""
    m = _VER_RE.match(version or "")
    return tuple(int(g or 0) for g in m.groups()) if m else _OLDEST


def known_coins(version: str | None) -> list[str]:
    v = parse(version)
    return [c for c in catalog.coins() if COIN_SINCE.get(c, _OLDEST) <= v]


def is_rejection(error: str | None) -> bool:
    """Client hat den Auftrag gar nicht erst gestartet – sagt nichts über die Grafikkarte."""
    return str(error or "").startswith("job_rejected:")
