"""On-Chain-Import-Routen — /api/modules/cryptoboard/portfolio/import/onchain/{preview,commit}.

preview — verknüpfte Base/Ethereum-Adresse (address_id) → erkannte Swaps als
          sell/buy-Vorschläge (EUR), dazu wraps, unklar, truncated/before_block
commit  — bestätigte Einträge ins FIFO-Ledger, Dedup über import_hash

Login-pflichtig, strikt user-scoped, nur lesend gegenüber der Chain. Alchemy-
Fehler werden auf feste Codes abgebildet — nie Rohtext, nie URL, nie Key.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import addresses_store, alchemy_client as ac, alchemy_key, onchain_import

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]

_STATUS_BY_CODE = {
    "address_not_found": status.HTTP_404_NOT_FOUND,
    "onchain_chain_not_supported": status.HTTP_400_BAD_REQUEST,
    "alchemy_key_missing": status.HTTP_409_CONFLICT,
    "alchemy_key_invalid": status.HTTP_401_UNAUTHORIZED,
    "alchemy_base_not_enabled": status.HTTP_403_FORBIDDEN,
    "alchemy_network_error": status.HTTP_502_BAD_GATEWAY,
    "alchemy_fetch_failed": status.HTTP_502_BAD_GATEWAY,
    "cryptoboard_onchain_disabled": status.HTTP_503_SERVICE_UNAVAILABLE,
}
_BLOCK_RE = r"^0x[0-9a-fA-F]{1,16}$"


def _fail(code: str):
    return coded(_STATUS_BY_CODE.get(code, status.HTTP_400_BAD_REQUEST), code)


class OnchainPreviewIn(BaseModel):
    address_id: int = Field(gt=0)
    to_block: str | None = Field(default=None, pattern=_BLOCK_RE)


class OnchainCommitTx(BaseModel):
    coin_id: str | None = Field(default=None, max_length=80)
    symbol: str = Field(default="", max_length=20)
    name: str = Field(default="", max_length=120)
    kind: str = Field(pattern=r"^(buy|sell|transfer_out)$")
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = Field(default=None, ge=0)
    fee: Decimal | None = Field(default=None, ge=0)
    executed_at: str = Field(min_length=1, max_length=40)
    hash: str = Field(min_length=1, max_length=180)  # xchain:64hex:chain:0x64hex:kind kann >120 Zeichen sein


class OnchainCommitIn(BaseModel):
    transactions: list[OnchainCommitTx] = Field(max_length=4000)


def _alchemy_code(exc: Exception) -> str:
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


@router.post("/portfolio/import/onchain/preview")
async def onchain_preview(body: OnchainPreviewIn, auth: Auth) -> dict:
    user, _ = auth
    addr = addresses_store.get(user, body.address_id)
    if addr is None:
        raise _fail("address_not_found")
    if addr["chain"] not in onchain_import.CHAINS:
        raise _fail("onchain_chain_not_supported")
    if not ac.enabled():
        raise _fail("cryptoboard_onchain_disabled")
    key = alchemy_key.get_key(user)
    if not key:
        raise _fail("alchemy_key_missing")
    code: str | None = None
    try:
        return await onchain_import.build_preview(user, addr["chain"], addr["address"], key, body.to_block)
    except (ac.AlchemyDisabled, ac.AlchemyNetworkError, ac.AlchemyHttpError, ac.AlchemyApiError) as exc:
        code = _alchemy_code(exc)
    # außerhalb des except: keine Exception-Kette an der HTTP-Antwort
    raise _fail(code)


@router.post("/portfolio/import/onchain/commit")
def onchain_commit(body: OnchainCommitIn, auth: Auth) -> dict:
    user, _ = auth
    if not body.transactions:
        return {"ok": True, "imported": 0, "skipped": 0, "skipped_details": []}
    return onchain_import.commit_entries(user, body.transactions)
