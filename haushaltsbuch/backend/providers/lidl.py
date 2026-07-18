"""Experimenteller read-only Lidl-Plus-Adapter mit festen Endpunkten."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx

from hydrahive.credentials.models import Credential
from hydrahive.credentials.store import get_credential, save_credential

from ..lidl_config import (
    APP_VERSION, TICKETS_V2_URL, TICKETS_V3_URL, TOKEN_URL, enabled, token_headers,
)
from ..lidl_http import request_json
from ..lidl_normalize import normalize_receipt
from ..loyalty_models import ProviderCapabilities
from ..loyalty_provider import (
    AuthRequired, CapabilityUnavailable, InvalidProviderData, LoyaltyProviderAdapter,
    ProviderConnection, ProviderPage, ProviderUnavailable, SchemaChanged, TokenMetadata,
)
from ..loyalty_receipt_models import ProviderReceipt

_RECEIPT_ID = re.compile(r"^[A-Za-z0-9._-]{1,256}$")


class LidlPlusProvider(LoyaltyProviderAdapter):
    provider_id = "lidl_plus"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport
        self._access_tokens: dict[int, tuple[str, datetime]] = {}

    def prime_auth(
        self, connection_id: int, access_token: str, expires_at: datetime,
    ) -> None:
        if connection_id < 1 or not access_token or len(access_token) > 16_384:
            raise InvalidProviderData("lidl_access_token_invalid")
        if not isinstance(expires_at, datetime) or expires_at.utcoffset() is None:
            raise InvalidProviderData("lidl_access_expiry_invalid")
        self._access_tokens[connection_id] = (access_token, expires_at)

    def _access_token(self, connection_id: int) -> str | None:
        entry = self._access_tokens.get(connection_id)
        if entry is None:
            return None
        token, expires_at = entry
        if expires_at <= datetime.now(timezone.utc):
            self._access_tokens.pop(connection_id, None)
            return None
        return token

    @staticmethod
    def _check_connection(connection: ProviderConnection) -> None:
        if not enabled():
            raise ProviderUnavailable("lidl_feature_disabled")
        if connection.country_code != "DE" or connection.language_code != "de":
            raise InvalidProviderData("lidl_locale_unsupported")

    @staticmethod
    def _credential(connection: ProviderConnection) -> Credential:
        credential = get_credential(connection.credential_owner, connection.credential_ref)
        if credential is None or credential.type != "bearer" or not credential.value:
            raise AuthRequired()
        return credential

    async def refresh_auth(self, connection: ProviderConnection) -> TokenMetadata:
        self._check_connection(connection)
        credential = self._credential(connection)
        payload = await request_json(
            "POST", TOKEN_URL, headers=token_headers(),
            data={"grant_type": "refresh_token", "refresh_token": credential.value},
            transport=self._transport,
        )
        if not isinstance(payload, dict) or not isinstance(
            payload.get("access_token"), str
        ):
            raise SchemaChanged("lidl_token_shape_changed")
        access_token = payload["access_token"]
        if not access_token or len(access_token) > 16_384:
            raise SchemaChanged("lidl_token_shape_changed")
        new_refresh = payload.get("refresh_token", credential.value)
        if not isinstance(new_refresh, str) or not new_refresh or len(new_refresh) > 16_384:
            raise SchemaChanged("lidl_token_shape_changed")
        expires = payload.get("expires_in")
        if type(expires) is not int or not 0 < expires <= 86_400:
            raise SchemaChanged("lidl_token_shape_changed")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires)
        rotated = new_refresh != credential.value
        if rotated:
            saved, _ = save_credential(
                connection.credential_owner,
                Credential(
                    credential.name, credential.type, new_refresh,
                    credential.url_pattern, credential.description,
                    credential.header_name, credential.query_param,
                ),
            )
            if not saved:
                raise ProviderUnavailable("lidl_credential_rotation_failed")
        self._access_tokens[connection.connection_id] = (access_token, expires_at)
        return TokenMetadata(expires_at=expires_at, rotated=rotated)

    async def probe(self, connection: ProviderConnection) -> ProviderCapabilities:
        if self._access_token(connection.connection_id) is None:
            await self.refresh_auth(connection)
        return ProviderCapabilities(
            receipts=True, receipt_items=True, discounts=True, deposits=True,
            token_refresh=True,
        )

    def _headers(self, connection: ProviderConnection) -> dict[str, str]:
        token = self._access_token(connection.connection_id)
        if token is None:
            raise AuthRequired()
        return {
            "Authorization": f"Bearer {token}",
            "App": "com.lidl.eci.lidl.plus",
            "App-Version": APP_VERSION,
            "Operating-System": "iOs",
            "Country": "DE",
            "Accept-Language": "de-DE",
        }

    async def list_receipts(
        self, connection: ProviderConnection, cursor: str | None, page_size: int
    ) -> ProviderPage[str]:
        self._check_connection(connection)
        if not 1 <= page_size <= 500:
            raise InvalidProviderData("page_size_invalid")
        try:
            page_number = int(cursor) if cursor is not None else 1
        except ValueError as exc:
            raise InvalidProviderData("cursor_invalid") from exc
        if page_number < 1 or page_number > 100:
            raise InvalidProviderData("cursor_invalid")
        url = (
            f"{TICKETS_V2_URL}/DE/tickets?"
            f"pageNumber={page_number}&onlyFavorite=false"
        )
        payload = await request_json(
            "GET", url, headers=self._headers(connection), transport=self._transport
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("tickets"), list):
            raise SchemaChanged("lidl_ticket_list_shape_changed")
        ids: list[str] = []
        for item in payload["tickets"]:
            value = item.get("id") if isinstance(item, dict) else None
            if not isinstance(value, str) or not _RECEIPT_ID.fullmatch(value):
                raise SchemaChanged("lidl_ticket_id_invalid")
            ids.append(value)
        try:
            total, size = int(payload.get("totalCount")), int(payload.get("size"))
        except (TypeError, ValueError):
            total, size = 0, 0
        has_more = payload.get("hasMore") is True
        if size > 0:
            has_more = page_number * size < total
        return ProviderPage(ids, str(page_number + 1) if has_more else None)

    async def get_receipt(
        self, connection: ProviderConnection, provider_receipt_id: str
    ) -> ProviderReceipt:
        if not _RECEIPT_ID.fullmatch(provider_receipt_id):
            raise InvalidProviderData("receipt_id_invalid")
        self._check_connection(connection)
        payload = await request_json(
            "GET", f"{TICKETS_V3_URL}/DE/tickets/{provider_receipt_id}",
            headers=self._headers(connection), transport=self._transport,
        )
        if not isinstance(payload, dict):
            raise SchemaChanged("lidl_ticket_shape_changed")
        receipt = normalize_receipt(payload)
        if receipt.provider_id != provider_receipt_id:
            raise SchemaChanged("lidl_ticket_id_mismatch")
        return receipt

    async def get_balance(self, connection):
        raise CapabilityUnavailable("balance")

    async def list_expirations(self, connection):
        raise CapabilityUnavailable("expirations")

    async def list_activities(self, connection, cursor, page_size):
        raise CapabilityUnavailable("activities")

    async def list_coupons(self, connection, cursor, page_size):
        raise CapabilityUnavailable("coupons")

    async def list_partners(self, connection):
        raise CapabilityUnavailable("partners")

    def forget_auth(self, connection_id: int) -> None:
        self._access_tokens.pop(connection_id, None)

    async def disconnect(self, connection: ProviderConnection) -> None:
        # Ein laufender Sync besitzt keine offenen Handles; gültige Tokens bleiben bis Ablauf.
        self._access_token(connection.connection_id)
