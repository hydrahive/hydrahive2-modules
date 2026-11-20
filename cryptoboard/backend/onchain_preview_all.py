"""Trades ALLER Adressen (Base/Ethereum/Tron) in EINEM Preview — Vertrag 1.7.0.

Ablauf je Nutzer (Adress-Abruf selbst in onchain_fetch_all.collect_all):
  1. Jede verknüpfte Base/Ethereum-Adresse einzeln abrufen. Fehler einer
     Adresse brechen den GESAMTLAUF NICHT ab — sie landen als status
     "fehler" in `addresses`, die übrigen Adressen laufen normal weiter
     (anders als build_preview für eine einzelne Adresse, wo ein Alchemy-
     Fehler die Route scheitern lässt).
  2. "unklar"-Items mit reason nur_raus/nur_rein je EVM-Adresse -> xchain_build:
     nur_raus wird IMMER eine Ausgabe (transfer_out); nur_rein wird entweder
     Spam oder Pairing-Kandidat.
  3. Jede verknüpfte Tron-Adresse: Abgänge (from = eigene Adresse) sind
     Pairing-"sells", Eingänge generisches "unklar" (reason nur_rein, chain
     tron) — es gibt keine Gegenrichtung TRX->TRX zu paaren.
  4. HIER (preview_all): xchain_pairing.pair_all über ALLE gesammelten Tron-
     Abgänge und EVM-Pairing-Kandidaten -> pairs/mehrdeutig/unklar_tron.
     Verbrauchte EVM-Kandidaten (consumed) werden NICHT zusätzlich als
     "unklar" gezeigt.
  5. Erkannte Swaps je EVM-Adresse -> onchain_import.process_swaps
     (identischer Preis-/Gas-Kern wie beim Einzel-Preview).
  6. Alles mischen, zählen, Duplikate markieren.

Kurse: Alle benötigten coin_ids (Swaps + Ausgaben + Pairing-Kandidaten +
"tron" für die TRX-Gebühr) laufen durch EINEN gemeinsamen Kurs-Vorlauf —
pro Coin höchstens ein CoinGecko-Abruf für den GESAMTEN preview_all-Lauf,
nicht je Adresse.
"""
from __future__ import annotations

from . import onchain_import as oi, onchain_resolve as rs, portfolio_store as store
from . import xchain_pairing as xp
from .onchain_fetch_all import collect_all
from .onchain_rules import mark_bookable

EVM_CHAINS = oi.CHAINS  # ("base", "ethereum")


def _needed_day(needed: dict[str, str | None], coin_id: str | None, day: str | None) -> None:
    if not coin_id:
        return
    prev = needed.get(coin_id)
    needed[coin_id] = day if prev is None or (day is not None and day > prev) else prev


def _rebuild_ausgabe_price(entry: dict) -> dict:
    """Preis einer Ausgabe nach (eventuell verspätetem) Kurs-Nachladen neu ziehen — nur der Preis-Pfad."""
    if entry["coin_id"] is None or entry["price"] is not None:
        return entry
    day = rs.day_of(entry.get("executed_at"))
    price = rs.day_price(entry["coin_id"], day)
    if price is None:
        return entry
    entry = dict(entry)
    entry["price"] = oi.dec_str(price)
    entry["preis_fehlt"] = False
    return entry


async def _resolve_prices(data: dict, key: str) -> tuple[list[dict], bool]:
    """Alle Swaps über process_swaps (ein gemeinsamer Kurs-Vorlauf), Ausgaben-Preise danach nachziehen."""
    extra_needed: dict[str, str | None] = {"tron": None}
    for s in data["tron_sells"]:
        _needed_day(extra_needed, "tron", rs.day_of(s["executed_at"]))
    for c in data["candidates"]:
        _needed_day(extra_needed, c["coin_id"], rs.day_of(c["executed_at"]))
    for a in data["ausgaben"]:
        _needed_day(extra_needed, a["coin_id"], rs.day_of(a.get("executed_at")))

    transactions: list[dict] = []
    kurs_abruf_fehlgeschlagen = False
    if data["detected"]:
        for i, (chain, address, detected, grouped) in enumerate(data["detected"]):
            entries, failed = await oi.process_swaps(
                chain, address, key, detected, grouped, extra_needed=extra_needed if i == 0 else None)
            transactions.extend(entries)
            kurs_abruf_fehlgeschlagen = kurs_abruf_fehlgeschlagen or failed
    elif len(extra_needed) > 1 or any(extra_needed.values()):
        # Keine EVM-Adresse mit Swaps, aber Pairing-Kandidaten/Ausgaben/Tron-Gebühr brauchen trotzdem Kurse.
        try:
            await rs.ensure_prices_cached(extra_needed)
        except Exception:
            kurs_abruf_fehlgeschlagen = True

    data["ausgaben"] = [_rebuild_ausgabe_price(a) for a in data["ausgaben"]]
    return transactions, kurs_abruf_fehlgeschlagen


def _all_entries(transactions: list[dict], pairs_out: list[dict], mehrdeutig: list[dict],
                 ausgaben: list[dict]) -> list[dict]:
    return (transactions + [e for pr in pairs_out for e in pr["entries"]]
            + [e for m in mehrdeutig for c in m["candidates"] for e in c["entries"]] + ausgaben)


async def preview_all(user: str, key: str, *, window_minutes: int = xp.DEFAULT_WINDOW_MINUTES) -> dict:
    """Haupteinstieg der Route /portfolio/import/onchain/preview_all."""
    data = await collect_all(user, key, EVM_CHAINS)

    paired = xp.pair_all(data["tron_sells"], data["candidates"], data["own_addresses"],
                          window_minutes=window_minutes)
    consumed = paired["consumed"]
    # Spam steht NUR in "spam" – nie zusätzlich unter "unklar".
    spam_keys = {(sp["chain"], str(sp["hash"]).lower()) for sp in data["spam"]}
    unconsumed_generic = [
        oi.compact_unklar(chain, address, item)
        for chain, address, detected, _grouped in data["detected"]
        for item in detected["unklar"]
        if item.get("reason") == "nur_rein"
        and (chain, str(item["hash"]).lower()) not in consumed
        and (chain, str(item["hash"]).lower()) not in spam_keys
    ]

    transactions, kurs_abruf_fehlgeschlagen = await _resolve_prices(data, key)

    pairs_out = [
        {"id": f"xchain:{p['tron_tx']}:{p['evm_chain']}:{p['evm_tx']}", "tron_tx": p["tron_tx"],
         "evm_chain": p["evm_chain"], "evm_tx": p["evm_tx"], "sell_at": p["sell_at"], "buy_at": p["buy_at"],
         "delay_seconds": p["delay_seconds"], "entries": p["entries"]}
        for p in paired["pairs"]
    ]
    unklar_all = data["generic_unklar"] + unconsumed_generic + data["tron_unklar"] + paired["unklar_tron"]

    everything = _all_entries(transactions, pairs_out, paired["mehrdeutig"], data["ausgaben"])
    # Dieselbe Regel wie der Commit (onchain_rules.skip_reason) – setzt duplicate, buchbar, nicht_buchbar_grund.
    mark_bookable(everything, store.existing_hashes(user, [e["hash"] for e in everything]))
    # counts.buchbar: sofort buchbare Swaps/Paare (Ausgaben und Mehrdeutiges sind Opt-in, zählen nicht mit).
    buchbar = sum(1 for e in transactions + [e for pr in pairs_out for e in pr["entries"]] if e["buchbar"])

    return {
        "addresses": data["address_status"],
        "transactions": transactions,
        "pairs": pairs_out,
        "mehrdeutig": paired["mehrdeutig"],
        "ausgaben": data["ausgaben"],
        "spam": data["spam"],
        "wraps": data["wraps"],
        "unklar": unklar_all,
        "kurs_abruf_fehlgeschlagen": kurs_abruf_fehlgeschlagen,
        "window_minutes": window_minutes,
        "counts": {
            "swaps": sum(len(d["swaps"]) for _c, _a, d, _g in data["detected"]),
            "transactions": len(transactions),
            "wraps": len(data["wraps"]),
            "unklar": len(unklar_all),
            "duplicates": sum(1 for e in transactions if e["duplicate"]),
            "preis_fehlt": sum(1 for e in transactions if e["preis_fehlt"]),
            "gebuehr_fehlt": sum(1 for e in transactions if e["gebuehr_fehlt"]),
            "unresolved": sum(1 for e in transactions if not e["resolved"]),
            "pairs": len(pairs_out),
            "mehrdeutig": len(paired["mehrdeutig"]),
            "ausgaben": len(data["ausgaben"]),
            "spam": len(data["spam"]),
            "buchbar": buchbar,
        },
    }
