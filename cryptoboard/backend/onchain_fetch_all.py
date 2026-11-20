"""preview_all — Adress-Abruf + Fehlerklassifizierung je Chain (Base/Ethereum via Alchemy, Tron via tronscan).

Ausgelagert aus onchain_preview_all.py (Datei-Größenlimit ~200 Zeilen): reine
Netz-Kapselung, kein Pairing/Preis — das bleibt im Orchestrator. Ein Fehler
einer einzelnen Adresse wird HIER gefangen und als Status-Dict zurückgegeben,
nie weitergeworfen — preview_all soll bei einer kaputten Adresse nicht den
gesamten Lauf abbrechen.
"""
from __future__ import annotations

from . import alchemy_client as ac
from . import onchain_swaps as sw
from . import tron_history as th


def alchemy_error_code(exc: Exception) -> str:
    """Dieselbe Klassifizierung wie onchain_import_routes._alchemy_code, aber als
    String statt HTTP-Fehler — preview_all zeigt Adress-Fehler statt die Route scheitern zu lassen."""
    from . import alchemy_key  # lokal: zirkulärer Import vermeiden (alchemy_key importiert nichts von hier)

    if isinstance(exc, ac.AlchemyDisabled):
        return "cryptoboard_onchain_disabled"
    if isinstance(exc, ac.AlchemyNetworkError):
        return "alchemy_network_error"
    if isinstance(exc, ac.AlchemyHttpError):
        return alchemy_key._classify_http_error(exc.status_code, exc.body).replace(
            "alchemy_test_failed", "alchemy_fetch_failed")
    if isinstance(exc, ac.AlchemyApiError):
        return alchemy_key._classify_api_error(exc.rpc_message).replace(
            "alchemy_test_failed", "alchemy_fetch_failed")
    return "alchemy_fetch_failed"


def tron_error_code(exc: Exception) -> str:
    if isinstance(exc, th.TronDisabled):
        return "cryptoboard_onchain_disabled"
    if isinstance(exc, th.TronNetworkError):
        return "tron_network_error"
    return "tron_fetch_failed"


async def fetch_evm_address(chain: str, address: str, key: str) -> dict:
    """Ein EVM-Adress-Abruf -> {"status": "ok"|"fehler", "error": str|None, "truncated", "before_block",
    "detected": dict|None, "grouped": dict|None}."""
    try:
        fetched = await ac.fetch_transfers(chain, key, address, to_block="latest")
    except (ac.AlchemyDisabled, ac.AlchemyNetworkError, ac.AlchemyHttpError, ac.AlchemyApiError) as exc:
        return {"status": "fehler", "error": alchemy_error_code(exc), "truncated": False,
                "before_block": None, "detected": None, "grouped": None}
    transfers = fetched["transfers"]
    detected = sw.detect_swaps(chain, address, transfers)
    grouped = sw.group_by_hash(transfers)
    return {"status": "ok", "error": None, "truncated": bool(fetched.get("truncated")),
            "before_block": fetched.get("before_block"), "detected": detected, "grouped": grouped}


async def fetch_tron_address(address: str) -> dict:
    """Ein Tron-Adress-Abruf -> {"status", "error", "truncated", "transfers": list|None}."""
    try:
        fetched = await th.fetch_transfers(address)
    except (th.TronDisabled, th.TronNetworkError, th.TronFetchFailed) as exc:
        return {"status": "fehler", "error": tron_error_code(exc), "truncated": False, "transfers": None}
    return {"status": "ok", "error": None, "truncated": bool(fetched.get("truncated")),
            "transfers": fetched["transfers"]}


def _generic_unklar(chain: str, address: str, detected: dict) -> list[dict]:
    """EVM-"unklar"-Items, die NICHT in Ausgabe/Kandidat/Spam aufgelöst werden (mehrere_assets etc.)."""
    from . import onchain_import as oi
    return [oi.compact_unklar(chain, address, u) for u in detected["unklar"]
            if u.get("reason") not in ("nur_raus", "nur_rein")]


async def _split_unklar(chain: str, detected: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """EVM-"unklar"-Items einer Adresse -> (ausgaben, candidates, spam). Items mit anderem reason
    (mehrere_assets, decimals_fehlt, keine_nettobewegung) bleiben außen vor (siehe _generic_unklar)."""
    from . import xchain_build as xb

    ausgaben: list[dict] = []
    candidates: list[dict] = []
    spam: list[dict] = []
    for item in detected["unklar"]:
        if item.get("reason") == "nur_raus":
            ausgaben.append(await xb.build_ausgabe(chain, item))
        elif item.get("reason") == "nur_rein":
            kind, payload = await xb.classify_incoming(chain, item)
            (spam if kind == "spam" else candidates).append(payload)
    return ausgaben, candidates, spam


async def collect_all(user: str, key: str, evm_chains: tuple[str, ...]) -> dict:
    """Alle verknüpften Adressen abrufen -> gesammelte Rohdaten für Pairing/Preis-Vorlauf
    (preview_all.preview_all). Eine kaputte Adresse bricht den Gesamtlauf nicht ab."""
    from . import addresses_store, onchain_import as oi
    from . import xchain_build as xb

    addrs = addresses_store.list_for(user)
    out: dict = {
        "address_status": [], "detected": [], "ausgaben": [], "candidates": [], "spam": [],
        "generic_unklar": [], "wraps": [], "tron_sells": [], "tron_unklar": [],
        "own_addresses": {a["address"].lower() for a in addrs},
    }
    for addr in addrs:
        if addr["chain"] in evm_chains:
            res = await fetch_evm_address(addr["chain"], addr["address"], key)
            out["address_status"].append({
                "id": addr["id"], "chain": addr["chain"], "address": addr["address"], "label": addr["label"],
                "status": res["status"], "error": res["error"],
                "truncated": res["truncated"], "before_block": res["before_block"],
            })
            if res["status"] != "ok":
                continue
            detected, grouped = res["detected"], res["grouped"]
            out["detected"].append((addr["chain"], addr["address"], detected, grouped))
            out["wraps"].extend(oi.compact_wrap(w) for w in detected["wraps"])
            out["generic_unklar"].extend(_generic_unklar(addr["chain"], addr["address"], detected))
            ausgaben, candidates, spam = await _split_unklar(addr["chain"], detected)
            out["ausgaben"].extend(ausgaben)
            out["candidates"].extend(candidates)
            out["spam"].extend(spam)
        elif addr["chain"] == "tron":
            res = await fetch_tron_address(addr["address"])
            out["address_status"].append({
                "id": addr["id"], "chain": "tron", "address": addr["address"], "label": addr["label"],
                "status": res["status"], "error": res["error"],
                "truncated": res["truncated"], "before_block": None,
            })
            if res["status"] != "ok":
                continue
            addr_lower = addr["address"].lower()
            for t in res["transfers"]:
                if t["from"].lower() == addr_lower:
                    out["tron_sells"].append(xb.tron_sell_from_transfer(t))
                elif t["to"].lower() == addr_lower:
                    out["tron_unklar"].append(xb.tron_incoming_unklar(t))
    return out
