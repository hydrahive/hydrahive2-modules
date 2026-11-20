"""Read-Port v2 — Wallet-Bestände (Haushaltsbuch Etappe A2, VERTRAG-PORT-V2.md).

Ausgelagert aus read_port.py (Datei-Größenlimit ~200 Zeilen); read_port.py
re-exportiert diese Namen, bleibt der EINE Einstiegspunkt für andere Module.

Bewertung NICHT neu erfunden: wallets.balances_for_addresses (dieselbe
Logik wie die Wallets-Ansicht des Cryptoboards selbst — Kurs via CoinGecko,
TRC20-Token ohne coin_id über price_trx × TRX-EUR). Der Gesamtwert für eine
Adressmenge entspricht dadurch IMMER exakt dem, was die Wallets-Ansicht für
dieselben Adressen zeigen würde.
"""
from __future__ import annotations

from . import addresses_store
from . import wallets


class WalletAddressNotFound(LookupError):
    """Adress-ID unbekannt ODER gehört nicht dem User — bewusst nicht
    unterscheidbar (kein Existenz-Leak nach außen, wie PortfolioNotFound)."""


def wallet_addresses_for(username: str) -> list[dict]:
    """Eigene Cryptoboard-Adressen des Users — nie fremde (addresses_store.list_for
    filtert bereits auf "user")."""
    return [{"id": a["id"], "chain": a["chain"], "address": a["address"], "label": a["label"]}
            for a in addresses_store.list_for(username)]


async def wallet_holdings(username: str, address_ids: list[int], *, to_minor, quantity_str, now_iso) -> dict:
    """Bestand je Coin für die angegebenen EIGENEN Adressen, Kurse wie im Cryptoboard.

    `to_minor`/`quantity_str`/`now_iso` werden von read_port.py durchgereicht statt
    hier dupliziert zu werden (einzige Umrechnungslogik bleibt in read_port.py).
    Unbekannte/fremde address_id -> WalletAddressNotFound (kein Existenz-Leak).
    Unerwarteter Fehler beim Bestandsabruf -> PortfolioUnavailable (vom Aufrufer
    zu werfen, siehe read_port.py — hier nur die reine Logik).
    """
    own = {a["id"]: a for a in addresses_store.list_for(username)}
    selected: list[dict] = []
    for aid in address_ids:
        if aid not in own:
            raise WalletAddressNotFound(aid)
        selected.append(own[aid])

    result = await wallets.balances_for_addresses(selected)

    holdings: list[dict] = []
    complete = True
    for addr in result["addresses"]:
        for asset in addr["assets"]:
            value = asset.get("value")
            if value is None:
                complete = False
            holdings.append({
                "chain": addr["chain"], "address_id": addr["id"], "symbol": asset["symbol"],
                "coin_id": asset.get("coin_id"),
                "quantity": quantity_str(asset["amount"]),
                "value_minor": to_minor(value) if value is not None else None,
                "verified": bool(asset.get("verified")),
            })

    return {
        "currency": "EUR",
        "as_of": now_iso(),
        "complete": complete,
        "value_minor": to_minor(result["total"]),
        "addresses": [{"id": a["id"], "chain": a["chain"], "address": a["address"], "label": a["label"]}
                      for a in selected],
        "holdings": holdings,
    }
