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


_MAX_PAGES_PER_DIRECTION = 200  # Sicherheitsgrenze gegen Endlos-Paging (kaputte Mocks/API)


def _block_num(transfer: dict) -> int:
    raw = transfer.get("blockNum")
    if not raw:
        return 0
    try:
        return int(str(raw), 16)
    except (TypeError, ValueError):
        return 0


def _transfer_identity(t: dict) -> tuple:
    """Stabile Identität eines Transfers — dedupliziert Einträge, die BEIDE
    Richtungs-Abfragen liefern (from==to==address, z. B. Selbst-Überweisung)."""
    uid = t.get("uniqueId")
    if uid:
        return ("uid", uid)
    raw = t.get("rawContract") or {}
    return ("composite", t.get("hash"), t.get("category"), t.get("from"), t.get("to"),
            raw.get("address"), raw.get("value"))


async def _page_direction(chain: str, key: str, direction: str, address: str, to_block: str,
                           cutoff: "datetime") -> list[dict]:
    """Holt ALLE Seiten einer Richtung, bis pageKey endet ODER ein Transfer älter
    als `cutoff` auftaucht (order=desc → alles Folgende ist noch älter, weiteres
    Paging dieser Richtung lohnt sich nicht mehr). Die letzte Seite kann noch
    Transfers enthalten, die älter als cutoff sind — die endgültige Alters-/
    Count-Grenze zieht fetch_transfers über ALLE Blöcke BEIDER Richtungen
    gemeinsam (K3-Fix), nicht pro Richtung einzeln."""
    out: list[dict] = []
    page_key = None
    pages = 0
    while True:
        pages += 1
        params = [_transfer_params(direction, address, to_block, page_key)]
        result = await call(chain, key, "alchemy_getAssetTransfers", params)
        batch = (result or {}).get("transfers") or []
        out.extend(batch)
        hit_cutoff = any(
            (ts := _transfer_timestamp(t)) is not None and ts < cutoff
            for t in batch
        )
        page_key = (result or {}).get("pageKey")
        if hit_cutoff or not page_key or pages >= _MAX_PAGES_PER_DIRECTION:
            break
    return out


async def fetch_transfers(
    chain: str,
    key: str,
    address: str,
    *,
    to_block: str = "latest",
    max_transactions: int = MAX_TRANSACTIONS,
    max_age_years: int = MAX_AGE_YEARS,
) -> dict:
    """Transfer-Historie einer Adresse — fromAddress UND toAddress bis zur
    SELBEN Grenze (K3-Fix), über pageKey gepagt.

    K3: Beide Richtungen werden vollständig geholt (nicht erst fromAddress bis
    zum Abbruch, toAddress dann gar nicht mehr — das ließ Swaps am Rand als
    "nur raus" erscheinen). Die Grenze (max_transactions eindeutige Tx-Hashes
    ODER max_age_years zurück) wird an einer BLOCKGRENZE gezogen: alle
    Transfers aus dem abschneidenden Block und älter werden verworfen, nie
    mitten in einem Block geschnitten — jede zurückgegebene Tx (lebt in genau
    einem Block) bleibt mit Transfers beider Richtungen vollständig erhalten.

    Rückgabe: {"transfers": [...], "truncated": bool, "before_block": str|None}.
    `truncated=True` + `before_block` gesetzt (Hex) → ein Folgelauf mit
    `to_block=before_block` ist INKLUSIV und holt genau diesen Block vollständig
    nach, ohne Lücke und ohne die bereits gelieferten Blöcke zu wiederholen.
    """
    if not enabled():
        raise AlchemyDisabled()
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * max_age_years)

    candidates: list[dict] = []
    seen_identities: set[tuple] = set()
    for direction in ("fromAddress", "toAddress"):
        for t in await _page_direction(chain, key, direction, address, to_block, cutoff):
            identity = _transfer_identity(t)
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            candidates.append(t)

    by_block: dict[int, list[dict]] = {}
    for t in candidates:
        by_block.setdefault(_block_num(t), []).append(t)

    included_blocks: list[int] = []
    seen_hashes: set[str] = set()
    truncated = False
    before_block: int | None = None
    for block_num in sorted(by_block, reverse=True):
        items = by_block[block_num]
        block_ts = next((ts for t in items if (ts := _transfer_timestamp(t)) is not None), None)
        block_hashes = {t["hash"] for t in items if t.get("hash")}
        prospective = seen_hashes | block_hashes
        too_old = block_ts is not None and block_ts < cutoff
        too_many = len(prospective) > max_transactions
        if too_old or too_many:
            truncated = True
            before_block = block_num
            break
        seen_hashes = prospective
        included_blocks.append(block_num)

    transfers = [t for b in included_blocks for t in by_block[b]]
    return {
        "transfers": transfers,
        "truncated": truncated,
        "before_block": hex(before_block) if before_block is not None else None,
    }
