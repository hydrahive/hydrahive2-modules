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
_TRON_API = "https://apilist.tronscanapi.com/api/account"
_BTC_API = "https://blockstream.info/api/address"

# EVM-Chains: chain → (RPC-URL, native-coin_id, {contract: (symbol, coin_id, decimals)})
_EVM = {
    "base": (
        "https://mainnet.base.org", "ETH", "ethereum",
        {"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": ("USDC", "usd-coin", 6)},
    ),
    "ethereum": (
        "https://ethereum-rpc.publicnode.com", "ETH", "ethereum",
        {
            "0xdAC17F958D2ee523a2206206994597C13D831ec7": ("USDT", "tether", 6),
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": ("USDC", "usd-coin", 6),
        },
    ),
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


# ---------------------------------------------------------------- EVM (Base/Ethereum)
async def evm_balance(chain: str, address: str) -> list[dict]:
    rpc, native_sym, native_coin, tokens = _EVM[chain]
    out: list[dict] = []
    # native Coin (ETH)
    wei = await _rpc(rpc, "eth_getBalance", [address, "latest"])
    native = int(wei, 16) / 1e18 if wei else 0.0
    if native > 0:
        out.append({"symbol": native_sym, "amount": native, "coin_id": native_coin})
    # ERC-20 balanceOf(address)
    for contract, (sym, coin_id, dec) in tokens.items():
        data = "0x70a08231000000000000000000000000" + address[2:].lower()
        res = await _rpc(rpc, "eth_call", [{"to": contract, "data": data}, "latest"])
        bal = int(res, 16) / (10 ** dec) if res and res != "0x" else 0.0
        if bal > 0:
            out.append({"symbol": sym, "amount": bal, "coin_id": coin_id})
    return out


# ---------------------------------------------------------------- Tron
# Bekannte TRC20 (tokenId/Contract → coin_id) bekommen den CoinGecko-Kurs;
# alle ANDEREN Token werden trotzdem gezeigt (Wert via Tronscan price_trx,
# sonst "unbekannt") — nichts wird ausgeblendet, da auch obskure Token real
# wertvoll sein können.
_TRON_COIN_IDS = {"TRX": "tron", "USDT": "tether", "USDC": "usd-coin"}


async def tron_balance(address: str) -> list[dict]:
    data = await _get(f"{_TRON_API}?address={address}")
    out: list[dict] = []
    for tok in (data.get("tokenBalances") or []) if isinstance(data, dict) else []:
        symbol = (tok.get("tokenAbbr") or tok.get("tokenName") or "?").upper()
        try:
            amount = float(tok.get("balance", 0)) / (10 ** int(tok.get("tokenDecimal", 0)))
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        price_trx = tok.get("tokenPriceInTrx")
        out.append({
            "symbol": symbol,
            "amount": amount,
            "coin_id": _TRON_COIN_IDS.get(symbol),     # None → über price_trx bewerten
            "price_trx": price_trx if isinstance(price_trx, (int, float)) else None,
            "verified": bool(tok.get("vip")),
            "name": tok.get("tokenName") or "",
            "token_id": str(tok.get("tokenId") or ""),
        })
    return out


# ---------------------------------------------------------------- Bitcoin
async def btc_balance(address: str) -> list[dict]:
    data = await _get(f"{_BTC_API}/{address}")
    stats = data.get("chain_stats") or {} if isinstance(data, dict) else {}
    funded = int(stats.get("funded_txo_sum", 0))
    spent = int(stats.get("spent_txo_sum", 0))
    btc = (funded - spent) / 1e8
    return [{"symbol": "BTC", "amount": btc, "coin_id": "bitcoin"}] if btc > 0 else []


async def fetch_balance(chain: str, address: str) -> list[dict]:
    """Bestände einer Adresse. Fehler werden geloggt → leere Liste (eine kaputte
    Adresse/Chain bricht nicht die ganze Wallets-Ansicht)."""
    try:
        if chain in _EVM:
            return await evm_balance(chain, address)
        if chain == "tron":
            return await tron_balance(address)
        if chain == "bitcoin":
            return await btc_balance(address)
        return []
    except Exception as exc:
        logger.warning("chain_clients: %s/%s fehlgeschlagen: %s", chain, address[:10], exc)
        return []
