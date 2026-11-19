"""Alchemy-RPC-Client für On-Chain-Lesezugriffe — NUR Lesen, Methoden-Allowlist.

Netz-Call in EINER Funktion gekapselt (_rpc, Muster chain_clients._rpc), damit
Tests ihn mocken können, ohne echten Key/Netzzugriff. Jede Methode außerhalb
der Allowlist wird VOR dem Netzaufruf abgelehnt — lesend bleibt absolute
Grenze: kein Signieren, kein Senden.

Kill-Switch HH_CRYPTOBOARD_ONCHAIN_ENABLED (Default an) — Konvention wie
haushaltsbuch/backend/lidl_config.py (HH_HAUSHALTSBUCH_LIDL_ENABLED).

Der Alchemy-Key taucht NIE in einer Exception-Message oder einem Log auf:
httpx.HTTPStatusError.__str__() enthält die Request-URL (mit Key als
Pfadsegment!) — deshalb wird bei einem HTTP-Fehler NIE str(exc) verwendet,
nur exc.response.status_code.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

_TIMEOUT = 15.0

MAX_TRANSACTIONS = 1000
MAX_AGE_YEARS = 2

# Nur lesend. Jede andere Methode (sendRawTransaction, sendTransaction,
# personal_sign, ...) wird in call() VOR dem Netzaufruf abgelehnt.
ALLOWED_METHODS = frozenset({
    "alchemy_getAssetTransfers",
    "eth_getTransactionReceipt",
    "eth_blockNumber",
    "eth_getTransactionByHash",
})

_CHAIN_HOSTS = {
    "base": "base-mainnet.g.alchemy.com",
    "ethereum": "eth-mainnet.g.alchemy.com",
}


class MethodNotAllowed(ValueError):
    """Eine nicht gelistete (potenziell schreibende) Methode wurde abgelehnt."""


class ChainNotSupported(ValueError):
    """Chain ist keine der unterstützten Alchemy-Chains (base/ethereum)."""


class AlchemyDisabled(RuntimeError):
    """Kill-Switch HH_CRYPTOBOARD_ONCHAIN_ENABLED ist aus."""


class AlchemyHttpError(RuntimeError):
    """HTTP-Fehlerstatus von Alchemy — NIE die Original-Exception/URL weiterreichen (Key!).

    `body` ist NUR der Response-Body (Alchemy-Fehlertext, z. B. Plan-Hinweis),
    NIEMALS die Request-URL — die URL enthält den Key als Pfadsegment.
    """

    def __init__(self, status_code: int, body: str = "") -> None:
        super().__init__(f"alchemy_http_{status_code}")
        self.status_code = status_code
        self.body = body


class AlchemyNetworkError(RuntimeError):
    """Verbindungsfehler/Timeout — kein HTTP-Status vorhanden, kein Key im Text."""


class AlchemyApiError(RuntimeError):
    """JSON-RPC-Fehlerobjekt bei HTTP 200 (z. B. Plan-Grenze auf einer Chain)."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__("alchemy_api_error")
        self.rpc_code = code
        self.rpc_message = message


def enabled() -> bool:
    """Kill-Switch — Konvention wie lidl_config.enabled(): Default an."""
    value = os.getenv("HH_CRYPTOBOARD_ONCHAIN_ENABLED")
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off"}


def chain_url(chain: str, key: str) -> str:
    host = _CHAIN_HOSTS.get(chain)
    if host is None:
        raise ChainNotSupported(chain)
    return f"https://{host}/v2/{key}"


async def _rpc(url: str, method: str, params: list) -> Any:
    """Gekapselter Netz-Call — in Tests per monkeypatch ersetzt, kein echter Traffic."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as h:
        r = await h.post(url, json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # exc.response.text ist der Alchemy-Fehlertext (kein Key) — str(exc)/exc selbst
            # NIE weiterreichen, die enthält die Request-URL inkl. Key als Pfadsegment.
            body = exc.response.text[:500] if exc.response is not None else ""
            raise AlchemyHttpError(exc.response.status_code, body) from None
        payload = r.json()
        error = payload.get("error")
        if error:
            raise AlchemyApiError(error.get("code"), str(error.get("message") or ""))
        return payload.get("result")


async def call(chain: str, key: str, method: str, params: list) -> Any:
    """Einziger Zugang für RPC-Aufrufe — Kill-Switch + Allowlist VOR dem Netz."""
    if not enabled():
        raise AlchemyDisabled()
    if method not in ALLOWED_METHODS:
        raise MethodNotAllowed(method)
    url = chain_url(chain, key)
    try:
        return await _rpc(url, method, params)
    except httpx.HTTPError as exc:
        if isinstance(exc, (AlchemyHttpError, AlchemyApiError)):
            raise
        # Timeouts/Verbindungsfehler: NICHT str(exc) — kann die URL (mit Key) enthalten.
        raise AlchemyNetworkError() from None


def _transfer_params(direction: str, address: str, to_block: str, page_key: str | None) -> dict:
    p: dict[str, Any] = {
        "fromBlock": "0x0",
        "toBlock": to_block,
        direction: address,
        "category": ["external", "internal", "erc20"],
        "withMetadata": True,
        "order": "desc",
        "maxCount": "0x3e8",
    }
    if page_key:
        p["pageKey"] = page_key
    return p


def _transfer_timestamp(transfer: dict) -> datetime | None:
    raw = (transfer.get("metadata") or {}).get("blockTimestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_transfers(
    chain: str,
    key: str,
    address: str,
    *,
    to_block: str = "latest",
    max_transactions: int = MAX_TRANSACTIONS,
    max_age_years: int = MAX_AGE_YEARS,
) -> dict:
    """Transfer-Historie einer Adresse — fromAddress UND toAddress getrennt,
    über pageKey gepagt, bis max_transactions eindeutige Tx-Hashes ODER
    max_age_years zurück erreicht sind (je nachdem was zuerst eintritt).

    Rückgabe: {"transfers": [...], "truncated": bool, "before_block": str|None}.
    `truncated=True` + `before_block` gesetzt → ein Folgelauf mit
    `to_block=before_block` holt die nächste, ältere Tranche.
    """
    if not enabled():
        raise AlchemyDisabled()
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * max_age_years)
    seen_hashes: set[str] = set()
    transfers: list[dict] = []
    truncated = False
    before_block: str | None = None

    for direction in ("fromAddress", "toAddress"):
        if truncated:
            break
        page_key = None
        while True:
            params = [_transfer_params(direction, address, to_block, page_key)]
            result = await call(chain, key, "alchemy_getAssetTransfers", params)
            batch = (result or {}).get("transfers") or []
            stop = False
            for t in batch:
                ts = _transfer_timestamp(t)
                over_age = ts is not None and ts < cutoff
                h = t.get("hash")
                over_count = bool(h) and h not in seen_hashes and len(seen_hashes) >= max_transactions
                if over_age or over_count:
                    truncated = True
                    before_block = t.get("blockNum")
                    stop = True
                    break
                if h:
                    seen_hashes.add(h)
                transfers.append(t)
            if stop:
                break
            page_key = (result or {}).get("pageKey")
            if not page_key:
                break
    return {"transfers": transfers, "truncated": truncated, "before_block": before_block}
