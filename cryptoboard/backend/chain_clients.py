"""On-Chain-Bestände von Block-Explorern holen — keylos, NUR Lesen.

Drei Chains, je ein Fetcher; alle liefern eine einheitliche Liste von Assets:
  [{symbol, amount, coin_id}]  (coin_id = CoinGecko-ID für die €-Umrechnung)

Verifiziert (2026-06-24): base (mainnet.base.org RPC), tron (tronscanapi),
bitcoin (blockstream.info) — alle ohne API-Key. Netz-Calls in _rpc/_get
gekapselt → in Tests gemockt. Niemals Private Keys.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0

# Base-ERC20-Token, die wir auslesen: Contract → (symbol, coin_id, decimals)
_BASE_TOKENS = {
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": ("USDC", "usd-coin", 6),
}
_BASE_RPC = "https://mainnet.base.org"
_TRON_API = "https://apilist.tronscanapi.com/api/account"
_BTC_API = "https://blockstream.info/api/address"

# bekannte Tron-TRC20-Token (Contract → coin_id); TRX selbst separat
_TRON_TOKENS = {
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": ("USDT", "tether", 6),
}


async def _rpc(url: str, method: str, params: list) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as h:
        r = await h.post(url, json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
        r.raise_for_status()
        return r.json().get("result")


async def _get(url: str) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as h:
        r = await h.get(url)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------- Base / EVM
async def base_balance(address: str) -> list[dict]:
    out: list[dict] = []
    # native ETH
    wei = await _rpc(_BASE_RPC, "eth_getBalance", [address, "latest"])
    eth = int(wei, 16) / 1e18 if wei else 0.0
    if eth > 0:
        out.append({"symbol": "ETH", "amount": eth, "coin_id": "ethereum"})
    # ERC-20 balanceOf(address)
    for contract, (sym, coin_id, dec) in _BASE_TOKENS.items():
        data = "0x70a08231000000000000000000000000" + address[2:].lower()
        res = await _rpc(_BASE_RPC, "eth_call", [{"to": contract, "data": data}, "latest"])
        bal = int(res, 16) / (10 ** dec) if res and res != "0x" else 0.0
        if bal > 0:
            out.append({"symbol": sym, "amount": bal, "coin_id": coin_id})
    return out


# ---------------------------------------------------------------- Tron
async def tron_balance(address: str) -> list[dict]:
    data = await _get(f"{_TRON_API}?address={address}")
    out: list[dict] = []
    for tok in (data.get("tokenBalances") or []) if isinstance(data, dict) else []:
        abbr = (tok.get("tokenAbbr") or "").upper()
        try:
            amount = float(tok.get("balance", 0)) / (10 ** int(tok.get("tokenDecimal", 0)))
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        if abbr == "TRX":
            out.append({"symbol": "TRX", "amount": amount, "coin_id": "tron"})
        elif (tok.get("tokenId") or "") in _TRON_TOKENS:
            sym, coin_id, _ = _TRON_TOKENS[tok["tokenId"]]
            out.append({"symbol": sym, "amount": amount, "coin_id": coin_id})
    return out


# ---------------------------------------------------------------- Bitcoin
async def btc_balance(address: str) -> list[dict]:
    data = await _get(f"{_BTC_API}/{address}")
    stats = data.get("chain_stats") or {} if isinstance(data, dict) else {}
    funded = int(stats.get("funded_txo_sum", 0))
    spent = int(stats.get("spent_txo_sum", 0))
    btc = (funded - spent) / 1e8
    return [{"symbol": "BTC", "amount": btc, "coin_id": "bitcoin"}] if btc > 0 else []


_FETCHERS = {"base": base_balance, "tron": tron_balance, "bitcoin": btc_balance}


async def fetch_balance(chain: str, address: str) -> list[dict]:
    """Bestände einer Adresse. Fehler werden geloggt → leere Liste (eine kaputte
    Adresse/Chain bricht nicht die ganze Wallets-Ansicht)."""
    fetcher = _FETCHERS.get(chain)
    if fetcher is None:
        return []
    try:
        return await fetcher(address)
    except Exception as exc:
        logger.warning("chain_clients: %s/%s fehlgeschlagen: %s", chain, address[:10], exc)
        return []
