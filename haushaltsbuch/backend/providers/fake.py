"""Deterministischer Fake-Provider für Contract-, Sync- und UI-Tests."""
from __future__ import annotations

from collections.abc import Sequence

from ..loyalty_models import LoyaltyProvider, ProviderCapabilities
from ..loyalty_provider import (
    CapabilityUnavailable,
    LoyaltyProviderAdapter,
    ProviderActivity,
    ProviderBalance,
    ProviderConnection,
    ProviderCoupon,
    ProviderError,
    ProviderExpiration,
    ProviderPage,
    ProviderPartner,
    TokenMetadata,
)


class FakeLoyaltyProvider(LoyaltyProviderAdapter):
    def __init__(
        self,
        *,
        provider_id: LoyaltyProvider = "payback",
        capabilities: ProviderCapabilities | None = None,
        balance: ProviderBalance | None = None,
        expirations: Sequence[ProviderExpiration] = (),
        activities: Sequence[ProviderActivity] = (),
        coupons: Sequence[ProviderCoupon] = (),
        partners: Sequence[ProviderPartner] = (),
    ):
        self.provider_id = provider_id
        self.capabilities = capabilities or ProviderCapabilities()
        self.balance = balance
        self.expirations = list(expirations)
        self.activities = list(activities)
        self.coupons = list(coupons)
        self.partners = list(partners)
        self._failures: dict[str, ProviderError] = {}

    def fail_next(self, operation: str, error: ProviderError) -> None:
        self._failures[operation] = error

    def _before(self, operation: str, capability: str | None = None) -> None:
        failure = self._failures.pop(operation, None)
        if failure is not None:
            raise failure
        if capability and not getattr(self.capabilities, capability):
            raise CapabilityUnavailable(capability)

    @staticmethod
    def _page(items: list, cursor: str | None, page_size: int) -> ProviderPage:
        if page_size < 1 or page_size > 500:
            raise ValueError("page_size must be between 1 and 500")
        try:
            offset = int(cursor) if cursor is not None else 0
        except ValueError as exc:
            raise ValueError("cursor must be an integer offset") from exc
        if offset < 0:
            raise ValueError("cursor must not be negative")
        page = items[offset : offset + page_size]
        next_offset = offset + len(page)
        next_cursor = str(next_offset) if next_offset < len(items) else None
        return ProviderPage(items=list(page), next_cursor=next_cursor)

    async def probe(self, connection: ProviderConnection) -> ProviderCapabilities:
        self._before("probe")
        return self.capabilities.model_copy(deep=True)

    async def refresh_auth(self, connection: ProviderConnection) -> TokenMetadata:
        self._before("refresh_auth", "token_refresh")
        return TokenMetadata(rotated=False)

    async def get_balance(self, connection: ProviderConnection) -> ProviderBalance:
        self._before("get_balance", "balance")
        if self.balance is None:
            raise ValueError("fake balance data missing")
        return self.balance

    async def list_expirations(
        self, connection: ProviderConnection
    ) -> list[ProviderExpiration]:
        self._before("list_expirations", "expirations")
        return list(self.expirations)

    async def list_activities(
        self, connection: ProviderConnection, cursor: str | None, page_size: int
    ) -> ProviderPage[ProviderActivity]:
        self._before("list_activities", "activities")
        return self._page(self.activities, cursor, page_size)

    async def list_coupons(
        self, connection: ProviderConnection, cursor: str | None, page_size: int
    ) -> ProviderPage[ProviderCoupon]:
        self._before("list_coupons", "coupons")
        return self._page(self.coupons, cursor, page_size)

    async def list_partners(
        self, connection: ProviderConnection
    ) -> list[ProviderPartner]:
        self._before("list_partners", "partners")
        return list(self.partners)

    async def disconnect(self, connection: ProviderConnection) -> None:
        self._before("disconnect")
