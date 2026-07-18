from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pytest

from backend.loyalty_models import ProviderCapabilities
from backend.loyalty_provider import (
    AuthRequired,
    CapabilityUnavailable,
    ProviderActivity,
    ProviderBalance,
    ProviderConnection,
    ProviderCoupon,
    ProviderExpiration,
    ProviderPartner,
    RateLimited,
)
from backend.providers.fake import FakeLoyaltyProvider


def _connection() -> ProviderConnection:
    return ProviderConnection(
        connection_id=7,
        household_id=3,
        provider="payback",
        credential_ref="hh-payback-7",
        country_code="DE",
        language_code="de",
    )


def _provider() -> FakeLoyaltyProvider:
    return FakeLoyaltyProvider(
        capabilities=ProviderCapabilities(
            balance=True, expirations=True, activities=True, coupons=True, partners=True
        ),
        balance=ProviderBalance(observed_at=datetime(2026, 7, 18, tzinfo=timezone.utc), points=1234),
        expirations=[ProviderExpiration(expires_on=date(2026, 9, 30), points=200)],
        activities=[
            ProviderActivity(
                provider_id=f"a-{index}", fingerprint=f"fa-{index}",
                kind="earn", occurred_on=date(2026, 7, index + 1), points_delta=10,
                partner_provider_id="dm", description="Einkauf",
            )
            for index in range(3)
        ],
        partners=[ProviderPartner(provider_id="dm", name="dm")],
        coupons=[
            ProviderCoupon(
                provider_id="c-1", fingerprint="fc-1", title="10fach",
                partner_provider_id="dm", valid_until=date(2026, 8, 1),
            )
        ],
    )


def test_fake_provider_reports_only_configured_capabilities():
    result = asyncio.run(_provider().probe(_connection()))
    assert result.balance is True
    assert result.receipts is False


def test_fake_provider_pages_are_stable_and_cursor_based():
    provider = _provider()
    first = asyncio.run(provider.list_activities(_connection(), cursor=None, page_size=2))
    second = asyncio.run(provider.list_activities(_connection(), cursor=first.next_cursor, page_size=2))
    assert [item.provider_id for item in first.items] == ["a-0", "a-1"]
    assert [item.provider_id for item in second.items] == ["a-2"]
    assert second.next_cursor is None


def test_fake_provider_returns_provider_neutral_records():
    provider = _provider()
    balance = asyncio.run(provider.get_balance(_connection()))
    expirations = asyncio.run(provider.list_expirations(_connection()))
    partners = asyncio.run(provider.list_partners(_connection()))
    coupons = asyncio.run(provider.list_coupons(_connection(), None, 10))
    assert (balance.points, expirations[0].points) == (1234, 200)
    assert partners[0].provider_id == "dm"
    assert coupons.items[0].partner_provider_id == "dm"


def test_unavailable_capability_is_explicit_not_empty_data():
    provider = FakeLoyaltyProvider(capabilities=ProviderCapabilities())
    with pytest.raises(CapabilityUnavailable) as exc:
        asyncio.run(provider.get_balance(_connection()))
    assert exc.value.capability == "balance"


def test_configured_provider_error_is_propagated_once():
    provider = _provider()
    provider.fail_next("list_activities", RateLimited(retry_after_seconds=60))
    with pytest.raises(RateLimited) as exc:
        asyncio.run(provider.list_activities(_connection(), None, 10))
    assert exc.value.retry_after_seconds == 60
    assert len(asyncio.run(provider.list_activities(_connection(), None, 10)).items) == 3


def test_provider_error_persists_a_safe_stage_code():
    error = AuthRequired("lidl_refresh_rejected")
    assert error.code == "lidl_refresh_rejected"
    assert str(error) == "lidl_refresh_rejected"


def test_auth_failure_never_contains_credentials():
    provider = _provider()
    provider.fail_next("probe", AuthRequired())
    with pytest.raises(AuthRequired) as exc:
        asyncio.run(provider.probe(_connection()))
    assert str(exc.value) == "auth_required"
    assert _connection().credential_ref not in str(exc.value)


def test_page_size_and_cursor_are_validated():
    provider = _provider()
    with pytest.raises(ValueError, match="page_size"):
        asyncio.run(provider.list_activities(_connection(), None, 0))
    with pytest.raises(ValueError, match="cursor"):
        asyncio.run(provider.list_activities(_connection(), "not-an-int", 10))
