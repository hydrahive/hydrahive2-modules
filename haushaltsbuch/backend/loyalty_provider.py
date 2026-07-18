"""Provider-neutraler Vertrag für read-only Kundenkarten-Synchronisierung."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Generic, Literal, Protocol, TypeVar

from .loyalty_models import LoyaltyProvider, ProviderCapabilities

T = TypeVar("T")
ActivityKind = Literal["earn", "redeem", "expire", "reversal", "adjustment"]
CouponStatus = Literal["available", "activated", "redeemed", "expired", "unavailable"]


class ProviderError(RuntimeError):
    code = "provider_error"

    def __init__(self, code: str | None = None):
        super().__init__(code or self.code)


class AuthRequired(ProviderError):
    code = "auth_required"


class ForbiddenOrBlocked(ProviderError):
    code = "forbidden_or_blocked"


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"


class SchemaChanged(ProviderError):
    code = "schema_changed"


class InvalidProviderData(ProviderError):
    code = "invalid_provider_data"


class CapabilityUnavailable(ProviderError):
    code = "capability_unavailable"

    def __init__(self, capability: str):
        self.capability = capability
        super().__init__(f"{self.code}:{capability}")


class RateLimited(ProviderError):
    code = "rate_limited"

    def __init__(self, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__()


@dataclass(frozen=True, slots=True)
class ProviderConnection:
    connection_id: int
    household_id: int
    provider: LoyaltyProvider
    credential_ref: str
    credential_owner: str = ""
    country_code: str = "DE"
    language_code: str = "de"


@dataclass(frozen=True, slots=True)
class TokenMetadata:
    expires_at: datetime | None = None
    rotated: bool = False


@dataclass(frozen=True, slots=True)
class ProviderBalance:
    observed_at: datetime
    points: int
    money_value_minor: int | None = None
    money_value_currency: str | None = None
    valuation_version: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderExpiration:
    expires_on: date
    points: int
    status: Literal["scheduled", "expired", "cancelled"] = "scheduled"


@dataclass(frozen=True, slots=True)
class ProviderPartner:
    provider_id: str
    name: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class ProviderActivity:
    provider_id: str | None
    fingerprint: str
    kind: ActivityKind
    occurred_on: date
    points_delta: int
    partner_provider_id: str | None = None
    description: str | None = None
    provider_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProviderCoupon:
    provider_id: str | None
    fingerprint: str
    title: str
    partner_provider_id: str | None = None
    description: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    status: CouponStatus = "available"
    multiplier: str | None = None
    bonus_points: int | None = None
    condition_text: str | None = None
    provider_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProviderPage(Generic[T]):
    items: list[T] = field(default_factory=list)
    next_cursor: str | None = None


class LoyaltyProviderAdapter(Protocol):
    provider_id: LoyaltyProvider

    async def probe(self, connection: ProviderConnection) -> ProviderCapabilities: ...
    async def refresh_auth(self, connection: ProviderConnection) -> TokenMetadata: ...
    async def get_balance(self, connection: ProviderConnection) -> ProviderBalance: ...
    async def list_expirations(self, connection: ProviderConnection) -> list[ProviderExpiration]: ...
    async def list_activities(
        self, connection: ProviderConnection, cursor: str | None, page_size: int
    ) -> ProviderPage[ProviderActivity]: ...
    async def list_coupons(
        self, connection: ProviderConnection, cursor: str | None, page_size: int
    ) -> ProviderPage[ProviderCoupon]: ...
    async def list_partners(self, connection: ProviderConnection) -> list[ProviderPartner]: ...
    async def disconnect(self, connection: ProviderConnection) -> None: ...
