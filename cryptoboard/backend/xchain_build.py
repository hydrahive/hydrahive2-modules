"""Baut aus den rohen "nur_raus"/"nur_rein"-Unklar-Items (onchain_swaps) die
Zwischenformen für preview_all: Ausgaben-Entries, Pairing-Kandidaten, Spam-Einträge.

Reihenfolge je EVM-Adresse (siehe onchain_preview_all.py):
  nur_raus  -> coin_id auflösen, dann Spam-Prüfung (xchain_spam, Till 20.11.2026:
               Spam gilt auch bei Abgängen — gleiche Regeln, Kontrakt entscheidet).
               Spam -> Spam-Eintrag (nie Ausgabe). Sonst -> Ausgabe (kind
               transfer_out) — nie Pairing-Kandidat, da Pairing nur TRX-Abgang
               <-> EVM-EINGANG kennt.
  nur_rein  -> coin_id auflösen, dann Spam-Prüfung (xchain_spam). Spam -> Spam-
               Eintrag. Sonst -> Pairing-Kandidat für xchain_pairing.
Alle Netz-/DB-Zugriffe (resolve_coin_id, Tageskurs) laufen über die
bestehenden Module (onchain_resolve) — diese Datei selbst ruft nie das Netz
direkt auf.
"""
from __future__ import annotations

from decimal import Decimal

from . import onchain_import as oi
from . import onchain_resolve as rs
from . import xchain_spam as spam


def _dec_str(value: Decimal | None) -> str | None:
    return oi.dec_str(value)


def _spam_entry(chain: str, tx_hash: str, item: dict, asset: dict, symbol: str, contract: str | None,
                 grund: str) -> dict:
    qty = Decimal(int(asset["net"])).copy_abs() / (Decimal(10) ** int(asset["decimals"]))
    return {
        "hash": tx_hash.lower(), "chain": chain, "executed_at": oi.normalize_ts(item.get("executed_at")),
        "symbol": symbol[:20], "contract": contract, "amount": _dec_str(qty), "grund": grund,
    }


async def classify_outgoing(chain: str, item: dict) -> tuple[str, dict]:
    """nur_raus-Item -> ("spam", spam_entry) oder ("ausgabe", ausgabe_entry).

    Spiegelbild von classify_incoming: dieselben Spam-Regeln (xchain_spam,
    Kontrakt entscheidet immer) gelten auch für Abgänge (Till 20.11.2026) —
    ein Fake-Token verlässt die Wallet genauso "spam" wie er sie betritt.
    """
    asset = item["asset"]
    tx_hash = item["hash"]
    contract = asset.get("contract")
    symbol = str(asset.get("symbol") or "")
    res = await rs.resolve_coin_id(chain, contract, symbol)
    name = res.get("name") or ""
    grund = spam.classify_incoming(chain, contract, symbol, name, resolved=not res["unresolved"])
    if grund is not None:
        return "spam", _spam_entry(chain, tx_hash, item, asset, symbol, contract, grund)

    executed_at = oi.normalize_ts(item.get("executed_at"))
    qty = Decimal(int(asset["net"])).copy_abs() / (Decimal(10) ** int(asset["decimals"]))
    day = rs.day_of(item.get("executed_at"))
    price = rs.day_price(res["coin_id"], day) if res["coin_id"] else None
    ausgabe = {
        "hash": f"{chain}:{tx_hash.lower()}:transfer_out",
        "tx_hash": tx_hash.lower(),
        "coin_id": res["coin_id"],
        "symbol": symbol[:20].upper(),
        "name": name[:120],
        "kind": "transfer_out",
        "quantity": _dec_str(qty),
        "price": _dec_str(price),
        "fee": None,
        "executed_at": executed_at,
        "resolved": not res["unresolved"],
        "preis_fehlt": price is None,
        "gebuehr_fehlt": False,
        "duplicate": False,
    }
    return "ausgabe", ausgabe


async def classify_incoming(chain: str, item: dict) -> tuple[str, dict]:
    """nur_rein-Item -> ("spam", spam_entry) oder ("candidate", candidate_dict).

    candidate_dict passt zu xchain_pairing.pair_all's evm_incoming-Form:
    {evm_chain, evm_tx, executed_at, amount_base_units, decimals, coin_id,
     symbol, name, from, unresolved}.
    """
    asset = item["asset"]
    tx_hash = item["hash"]
    contract = asset.get("contract")
    symbol = str(asset.get("symbol") or "")
    res = await rs.resolve_coin_id(chain, contract, symbol)
    name = res.get("name") or ""
    grund = spam.classify_incoming(chain, contract, symbol, name, resolved=not res["unresolved"])
    if grund is not None:
        qty = Decimal(int(asset["net"])) / (Decimal(10) ** int(asset["decimals"]))
        return "spam", {
            "hash": tx_hash.lower(), "chain": chain, "executed_at": oi.normalize_ts(item.get("executed_at")),
            "symbol": symbol[:20], "contract": contract, "amount": _dec_str(qty), "grund": grund,
        }
    candidate = {
        "evm_chain": chain, "evm_tx": tx_hash.lower(),
        "executed_at": oi.normalize_ts(item.get("executed_at")),
        "amount_base_units": int(asset["net"]), "decimals": int(asset["decimals"]),
        "coin_id": res["coin_id"], "symbol": symbol, "name": name,
        "from": item.get("counterparty") or "", "unresolved": res["unresolved"],
    }
    return "candidate", candidate


def tron_sell_from_transfer(t: dict) -> dict:
    """tron_history-Transfer (from=Nutzeradresse) -> xchain_pairing-"sell"-Form."""
    return {
        "tron_tx": t["hash"], "executed_at": t["executed_at"],
        "amount_sun": t["amount_sun"], "fee_sun": t.get("fee_sun"),
        "from": t["from"], "to": t["to"],
    }


def tron_incoming_unklar(t: dict) -> dict:
    """Eingehender TRX-Transfer (to=Nutzeradresse) — generisches Unklar-Format
    (nicht Teil des Pairings; es gibt keine Gegenrichtung TRX->TRX zu paaren)."""
    from . import tron_history as th
    qty = th.sun_to_trx(int(t["amount_sun"]))
    return {
        "hash": t["hash"], "chain": "tron", "executed_at": t["executed_at"], "reason": "nur_rein",
        "tokens": [{"symbol": "TRX", "contract": None, "category": "native",
                    "direction": "rein", "amount": _dec_str(qty)}],
    }
