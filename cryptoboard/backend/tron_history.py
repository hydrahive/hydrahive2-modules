"""Tron-Transaktionshistorie — nur lesend, keylos, über tronscan.

Quelle: tronscan `/api/transaction?address=…&start=…&limit=50&sort=-timestamp`
(dasselbe Haus wie der bestehende `/api/account`-Bestandsabruf in
chain_clients.tron_balance — konsistente Datenquelle, keine zweite API nötig).
Fallback trongrid wurde NICHT gebraucht: tronscan liefert alle benötigten
Felder (siehe unten, geprüft per curl gegen eine öffentliche, fremde Adresse
am 20.11.2026 — Till-Adresse nicht nötig, nicht verwendet).

Geprüfte Felder (curl, SUCCESS-Response, normale Wallet-Adresse):
  total              int,  Top-Level, Gesamtzahl Treffer (für Paging-Ende)
  data[].hash         str,  64 Hex, OHNE 0x-Prefix
  data[].timestamp    int,  Millisekunden seit Epoch
  data[].ownerAddress str,  Absender (Base58, T…)
  data[].toAddress    str,  Empfänger (Base58, T…)
  data[].contractType int,  1 = natives TRX-Transfer (TransferContract);
                            31 = TriggerSmartContract – nur mit contractData.call_value > 0
                            (TRX an einen Kontrakt, z. B. swapEth): Menge = call_value,
                            Ziel = contractData.contract_address
  data[].confirmed    bool
  data[].contractRet  str,  "SUCCESS" bei erfolgreicher Ausführung
  data[].amount       str,  SUN als Dezimalstring, 1 TRX = 10**6 SUN (exakt int)
  data[].cost.fee     int,  SUN — Netzgebühr der AUSFÜHRENDEN (ownerAddress-)
                      Seite. 0 bei rein empfangenen TRX-Transfers (normal,
                      der Empfänger zahlt bei TransferContract keine Gebühr).

UNSICHER / nicht abschließend verifiziert (keine fremde Tx mit Gebühr > 0 bei
contractType=1 vorgefunden, nur bei contractType=31/TRC20 beobachtet):
  - ob cost.fee bei TRX-Transfers (contractType=1) JE > 0 wird (z. B. bei
    Account-Activation unterwegs). Darum wird cost.fee IMMER übernommen,
    wenn vorhanden (auch 0) und NIE geraten, wenn das Feld fehlt.
  - Top-Level "fee" (Leerstring in allen geprüften Treffern) wird NICHT
    genutzt — cost.fee ist die belastbare Quelle.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx

from . import alchemy_client as ac

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_API = "https://apilist.tronscanapi.com/api/transaction"
_PAGE_SIZE = 50
_MAX_PAGES = 400  # 400 * 50 = 20000 Rohtreffer-Obergrenze, weit über MAX_TRANSACTIONS

MAX_TRANSACTIONS = 1000
MAX_AGE_YEARS = 2

_SUCCESS = "SUCCESS"
_NATIVE_TRANSFER_TYPE = 1
# TriggerSmartContract: zählt NUR mit TRX-callValue > 0 (z. B. Swap-Dienst "swapEth"),
# dann als TRX-Abgang an den Kontrakt. Reine Kontraktaufrufe ohne TRX bleiben draußen.
_TRIGGER_CONTRACT_TYPE = 31
SUN_PER_TRX = 10**6


class TronDisabled(RuntimeError):
    """Kill-Switch HH_CRYPTOBOARD_ONCHAIN_ENABLED ist aus (gemeinsam mit Alchemy)."""


class TronNetworkError(RuntimeError):
    """Verbindungsfehler/Timeout — kein HTTP-Status vorhanden."""


class TronFetchFailed(RuntimeError):
    """HTTP-Fehlerstatus oder unlesbare Antwort — NIE den Rohtext weiterreichen."""

    def __init__(self, status_code: int | None = None) -> None:
        super().__init__("tron_fetch_failed")
        self.status_code = status_code


async def _get(params: dict) -> Any:
    """Gekapselter Netz-Call — in Tests per monkeypatch ersetzt (Muster chain_clients._get)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as h:
        r = await h.get(_API, params=params)
        r.raise_for_status()
        return r.json()


async def _fetch_page(address: str, start: int) -> dict:
    try:
        data = await _get({"address": address, "start": start, "limit": _PAGE_SIZE, "sort": "-timestamp"})
    except httpx.HTTPStatusError as exc:
        raise TronFetchFailed(exc.response.status_code if exc.response is not None else None) from None
    except httpx.HTTPError:
        raise TronNetworkError() from None
    if not isinstance(data, dict):
        raise TronFetchFailed()
    return data


def _ts_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _call_value_sun(tx: dict) -> int | None:
    """TRX-callValue (SUN) eines TriggerSmartContract-Aufrufs, sonst None."""
    data = tx.get("contractData") if isinstance(tx.get("contractData"), dict) else {}
    raw = data.get("call_value")
    try:
        value = int(str(raw)) if raw is not None else 0
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _is_eligible(tx: dict) -> bool:
    if tx.get("confirmed") is not True or tx.get("contractRet") != _SUCCESS:
        return False
    ctype = tx.get("contractType")
    if ctype == _NATIVE_TRANSFER_TYPE:
        return True
    return ctype == _TRIGGER_CONTRACT_TYPE and _call_value_sun(tx) is not None


def _normalize(tx: dict) -> dict | None:
    """Rohe tronscan-Zeile -> normalisierter Transfer, oder None bei fehlenden Pflichtfeldern."""
    tx_hash = tx.get("hash")
    ts = tx.get("timestamp")
    amount_raw = tx.get("amount")
    to_addr = tx.get("toAddress")
    if tx.get("contractType") == _TRIGGER_CONTRACT_TYPE:
        # Menge = TRX-callValue, Ziel = aufgerufener Kontrakt (nicht das evtl. abweichende Top-Level-amount).
        amount_raw = _call_value_sun(tx)
        data = tx.get("contractData") if isinstance(tx.get("contractData"), dict) else {}
        to_addr = data.get("contract_address") or to_addr
    if not tx_hash or ts is None or amount_raw is None:
        return None
    try:
        amount_sun = int(str(amount_raw))
        ts_ms = int(ts)
    except (TypeError, ValueError):
        return None
    cost = tx.get("cost") if isinstance(tx.get("cost"), dict) else {}
    fee_sun = cost.get("fee")
    try:
        fee_sun = int(fee_sun) if fee_sun is not None else None
    except (TypeError, ValueError):
        fee_sun = None
    return {
        "hash": str(tx_hash).lower(),
        "executed_at": _ts_to_iso(ts_ms),
        "timestamp_ms": ts_ms,
        "from": str(tx.get("ownerAddress") or "").strip(),
        "to": str(to_addr or "").strip(),
        "amount_sun": amount_sun,
        "fee_sun": fee_sun,
    }


def sun_to_trx(amount_sun: int) -> Decimal:
    """Exakte SUN -> TRX Umrechnung (1 TRX = 10**6 SUN) als Decimal."""
    return Decimal(amount_sun) / Decimal(SUN_PER_TRX)


async def fetch_transfers(address: str, *, max_transactions: int = MAX_TRANSACTIONS,
                           max_age_years: int = MAX_AGE_YEARS) -> dict:
    """Native TRX-Transfers einer Adresse (ein-/ausgehend), neueste zuerst.

    Grenzen wie Alchemy: höchstens max_transactions ODER max_age_years zurück
    (was zuerst erreicht wird). tronscan liefert absteigend sortiert über
    start/limit-Paging — die Grenze wird daher einfach beim ERSTEN Treffer
    gezogen, der sie überschreitet (kein Blockgrenzen-Problem wie bei Alchemy,
    da hier nicht nach fromAddress/toAddress getrennt abgefragt wird).

    Rückgabe: {"transfers": [...], "truncated": bool, "before_timestamp": int|None}.
    `before_timestamp` (ms) für einen Folgelauf — tronscan selbst hat keinen
    Zeitfilter-Parameter, daher wird im Folgelauf lokal bis dahin gefiltert
    (siehe xchain_pairing/preview_all: ruft erneut ab und verwirft Neueres).
    """
    if not ac.enabled():
        raise TronDisabled()
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * max_age_years)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    transfers: list[dict] = []
    truncated = False
    before_timestamp: int | None = None
    start = 0
    total: int | None = None
    pages = 0

    while True:
        pages += 1
        page = await _fetch_page(address, start)
        if total is None:
            try:
                total = int(page.get("total") or 0)
            except (TypeError, ValueError):
                total = 0
        rows = page.get("data") or []
        if not isinstance(rows, list) or not rows:
            break
        stop = False
        for raw in rows:
            if not _is_eligible(raw):
                continue
            norm = _normalize(raw)
            if norm is None:
                continue
            if norm["timestamp_ms"] < cutoff_ms:
                truncated = True
                before_timestamp = norm["timestamp_ms"]
                stop = True
                break
            if len(transfers) >= max_transactions:
                truncated = True
                before_timestamp = norm["timestamp_ms"]
                stop = True
                break
            transfers.append(norm)
        if stop:
            break
        start += _PAGE_SIZE
        if start >= total or pages >= _MAX_PAGES:
            break
    return {"transfers": transfers, "truncated": truncated, "before_timestamp": before_timestamp}
