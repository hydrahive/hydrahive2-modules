"""Chain-übergreifende Swap-Paarung: TRX-Abgang (Tron) ↔ Coin-Eingang (EVM).

Reine Funktionen, kein Netz: Preis/Gebühr nutzen nur bereits gecachte
DB-Werte (onchain_resolve.price_pair, price_history_store) — dieselbe
Lesepfad-Konvention wie onchain_resolve.py selbst.

Paarungsregel (Till, 2026-11-20):
  - TRX-Abgänge (from = Nutzer-Tron-Adresse) werden chronologisch aufsteigend
    abgearbeitet. Je Abgang: Kandidaten sind EVM-Eingänge AUF Adressen des
    Nutzers, NACH dem Abgang, innerhalb `window_minutes` (Default 15).
  - Eingang VOR dem Abgang zählt nie.
  - Absender des Eingangs darf KEINE eigene Adresse des Nutzers sein (über
    alle Chains, kleingeschrieben verglichen) — sonst wäre es eine eigene
    Umbuchung, kein Dienst-Swap.
  - Kein Kandidat → Abgang bleibt unklar (reason "nur_raus", chain "tron").
  - Genau ein Kandidat → Paar.
  - Mehrere Kandidaten → der zeitlich NÄCHSTE gewinnt. Sind die ZWEI
    nächsten gleich weit entfernt (gleiche Verzögerung in Sekunden) → KEIN
    Auto-Paar; der Abgang landet in "mehrdeutig" mit genau diesen beiden
    Kandidaten. Die Kandidaten bleiben für spätere Abgänge verfügbar (sie
    wurden ja nicht verbraucht).
  - Jeder Eingang wird höchstens einmal verbraucht (gepaart) — danach fällt
    er aus dem Kandidatenpool für folgende Abgänge heraus.

Preis/Gebühr: Tag = Tag des TRX-Abgangs (dokumentierte Wahl, nicht der Tag
des Eingangs — bei einer Verzögerung über Mitternacht bleibt der Abgangstag
der Referenzpunkt für Kurs UND Gebühr). price_pair bevorzugt die
Stablecoin-Seite; die TRX-Seite bekommt dann price = Wert/Menge. Netzgebühr
(fee_sun) wird über den TRX-Tageskurs in EUR umgerechnet und auf den
sell-Eintrag gebucht; fehlt fee_sun oder der TRX-Kurs, ist fee None mit
Flag "gebuehr_fehlt" (kein Blocker).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from . import onchain_resolve as rs
from . import tron_history as th

DEFAULT_WINDOW_MINUTES = 15


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _xchain_hash(tron_tx: str, evm_chain: str, evm_tx: str, kind: str) -> str:
    return f"xchain:{tron_tx.lower()}:{evm_chain}:{evm_tx.lower()}:{kind}"


def _pair_id(tron_tx: str, evm_chain: str, evm_tx: str) -> str:
    return f"xchain:{tron_tx.lower()}:{evm_chain}:{evm_tx.lower()}"


def _filter_foreign_senders(evm_incoming: list[dict], own_addresses: set[str]) -> list[dict]:
    """Eingänge, deren Absender eine eigene Adresse ist, sind keine Dienst-Swaps."""
    return [c for c in evm_incoming if str(c.get("from") or "").lower() not in own_addresses]


def match_candidates(
    tron_sells: list[dict], evm_incoming: list[dict], own_addresses: set[str],
    *, window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict:
    """Reine Zuordnung (ohne Preis/Entry) — Rückgabe {"matched": [...], "ambiguous": [...], "unmatched": [...]}.

    `matched`: [(sell, candidate)]. `ambiguous`: [(sell, [cand1, cand2])].
    `unmatched`: [sell]. Jeder evm_incoming-Eintrag wird höchstens einmal in
    `matched` verbraucht.
    """
    pool = _filter_foreign_senders(evm_incoming, own_addresses)
    sells_sorted = sorted(tron_sells, key=lambda s: _parse_ts(s["executed_at"]))
    used_keys: set[tuple] = set()
    matched: list[tuple[dict, dict]] = []
    ambiguous: list[tuple[dict, list[dict]]] = []
    unmatched: list[dict] = []
    window = window_minutes * 60

    for sell in sells_sorted:
        sell_at = _parse_ts(sell["executed_at"])
        candidates = []
        for cand in pool:
            key = (cand["evm_chain"], cand["evm_tx"])
            if key in used_keys:
                continue
            delay = (_parse_ts(cand["executed_at"]) - sell_at).total_seconds()
            if 0 <= delay <= window:
                candidates.append((delay, cand))
        if not candidates:
            unmatched.append(sell)
            continue
        candidates.sort(key=lambda dc: dc[0])
        if len(candidates) >= 2 and candidates[0][0] == candidates[1][0]:
            ambiguous.append((sell, [candidates[0][1], candidates[1][1]]))
            continue
        best_delay, best = candidates[0]
        used_keys.add((best["evm_chain"], best["evm_tx"]))
        matched.append((sell, best))
    return {"matched": matched, "ambiguous": ambiguous, "unmatched": unmatched}


def _qty_evm(cand: dict) -> Decimal:
    return Decimal(int(cand["amount_base_units"])) / (Decimal(10) ** int(cand["decimals"]))


def _tron_fee_eur(sell: dict, day: str | None) -> tuple[Decimal | None, bool]:
    fee_sun = sell.get("fee_sun")
    if fee_sun is None or day is None:
        return None, True
    fee_trx = th.sun_to_trx(int(fee_sun))
    series_price = rs.day_price("tron", day)
    if series_price is None:
        return None, True
    return fee_trx * series_price, False


def build_pair_entries(sell: dict, cand: dict) -> dict:
    """Ein (sell, cand)-Treffer -> {"tron_tx","evm_chain","evm_tx","sell_at","buy_at",
    "delay_seconds","entries":[sell_entry, buy_entry]}. Preis/Gebühr-Tag = Tag des Abgangs."""
    tron_tx = sell["tron_tx"]
    evm_chain, evm_tx = cand["evm_chain"], cand["evm_tx"]
    sell_at, buy_at = _parse_ts(sell["executed_at"]), _parse_ts(cand["executed_at"])
    day = rs.day_of(sell["executed_at"])

    qty_sell = th.sun_to_trx(int(sell["amount_sun"]))
    qty_buy = _qty_evm(cand)
    p_sell, p_buy, _ = rs.price_pair("tron", qty_sell, cand.get("coin_id"), qty_buy, day)
    fee, gebuehr_fehlt = _tron_fee_eur(sell, day)

    pair_id = _pair_id(tron_tx, evm_chain, evm_tx)
    sell_entry = {
        "hash": _xchain_hash(tron_tx, evm_chain, evm_tx, "sell"), "tx_hash": pair_id,
        "coin_id": "tron", "symbol": "TRX", "name": "", "kind": "sell",
        "quantity": _dec_str(qty_sell), "price": _dec_str(p_sell), "fee": _dec_str(fee),
        "executed_at": sell["executed_at"], "resolved": True,
        "preis_fehlt": p_sell is None, "gebuehr_fehlt": gebuehr_fehlt, "duplicate": False,
    }
    buy_entry = {
        "hash": _xchain_hash(tron_tx, evm_chain, evm_tx, "buy"), "tx_hash": pair_id,
        "coin_id": cand.get("coin_id"), "symbol": str(cand.get("symbol") or "")[:20],
        "name": (cand.get("name") or "")[:120], "kind": "buy",
        "quantity": _dec_str(qty_buy), "price": _dec_str(p_buy), "fee": _dec_str(Decimal(0)),
        "executed_at": cand["executed_at"], "resolved": not cand.get("unresolved", False),
        "preis_fehlt": p_buy is None, "gebuehr_fehlt": False, "duplicate": False,
    }
    return {
        "tron_tx": tron_tx, "evm_chain": evm_chain, "evm_tx": evm_tx,
        "sell_at": sell["executed_at"], "buy_at": cand["executed_at"],
        "delay_seconds": int((buy_at - sell_at).total_seconds()),
        "entries": [sell_entry, buy_entry],
    }


def _dec_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    s = format(value, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _unklar_tron(sell: dict) -> dict:
    qty = th.sun_to_trx(int(sell["amount_sun"]))
    return {
        "hash": sell["tron_tx"], "chain": "tron", "executed_at": sell["executed_at"],
        "reason": "nur_raus",
        "tokens": [{"symbol": "TRX", "contract": None, "category": "native",
                    "direction": "raus", "amount": _dec_str(qty)}],
    }


def _ambiguous_entry(sell: dict, cands: list[dict]) -> dict:
    sell_at = _parse_ts(sell["executed_at"])
    out_cands = []
    for cand in cands:
        pair = build_pair_entries(sell, cand)
        out_cands.append({
            "evm_chain": cand["evm_chain"], "evm_tx": cand["evm_tx"],
            "executed_at": cand["executed_at"], "symbol": cand.get("symbol"),
            "amount": _dec_str(_qty_evm(cand)),
            "delay_seconds": int((_parse_ts(cand["executed_at"]) - sell_at).total_seconds()),
            "entries": pair["entries"],
        })
    return {
        "tron_tx": sell["tron_tx"], "executed_at": sell["executed_at"], "symbol": "TRX",
        "amount": _dec_str(th.sun_to_trx(int(sell["amount_sun"]))), "candidates": out_cands,
    }


def pair_all(
    tron_sells: list[dict], evm_incoming: list[dict], own_addresses: set[str],
    *, window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict:
    """Haupteinstieg: Paarung + Entry-Aufbau. Rückgabe {"pairs","mehrdeutig","unklar_tron","consumed"}.

    `consumed` = {(evm_chain, evm_tx)} der verbrauchten Eingänge — der Aufrufer
    entfernt diese aus der allgemeinen unklar-Liste (nicht doppelt zeigen).
    """
    matched_data = match_candidates(tron_sells, evm_incoming, own_addresses, window_minutes=window_minutes)
    pairs = [build_pair_entries(sell, cand) for sell, cand in matched_data["matched"]]
    mehrdeutig = [_ambiguous_entry(sell, cands) for sell, cands in matched_data["ambiguous"]]
    unklar_tron = [_unklar_tron(sell) for sell in matched_data["unmatched"]]
    consumed = {(c["evm_chain"], c["evm_tx"]) for _, c in matched_data["matched"]}
    return {"pairs": pairs, "mehrdeutig": mehrdeutig, "unklar_tron": unklar_tron, "consumed": consumed}
