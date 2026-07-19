"""Convert the strict PAYBACK bridge wire model into persistence records."""

from __future__ import annotations

import hashlib
import json

from .loyalty_persistence import SyncPayload
from .loyalty_provider import (
    ProviderActivity,
    ProviderBalance,
    ProviderCoupon,
    ProviderExpiration,
    ProviderPartner,
)
from .payback_bridge_models import PaybackBridgeImport


def _fingerprint(kind: str, values: tuple[object, ...]) -> str:
    canonical = json.dumps(
        [kind, *values], ensure_ascii=False, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sync_payload(body: PaybackBridgeImport) -> SyncPayload:
    balance = None
    if body.balance is not None:
        balance = ProviderBalance(
            observed_at=body.balance.observed_at,
            points=body.balance.available_points,
        )
    expirations = [
        ProviderExpiration(
            expires_on=item.expiration_date, points=item.points, status=item.status
        )
        for item in body.expirations
    ]
    partners = [
        ProviderPartner(
            provider_id=item.provider_partner_id, name=item.name, active=item.active
        )
        for item in body.partners
    ]
    activities = [
        ProviderActivity(
            provider_id=item.provider_activity_id,
            fingerprint=_fingerprint(
                "activity",
                (
                    item.provider_activity_id,
                    item.activity_type,
                    item.activity_date,
                    item.points_delta,
                    item.partner_provider_id,
                    item.original_description,
                    item.purchase_amount_minor,
                    item.purchase_currency,
                ),
            ),
            kind=item.activity_type,
            occurred_on=item.activity_date,
            points_delta=item.points_delta,
            partner_provider_id=item.partner_provider_id,
            description=item.original_description,
            purchase_amount_minor=item.purchase_amount_minor,
            purchase_currency=item.purchase_currency,
            provider_updated_at=item.provider_updated_at,
        )
        for item in body.activities
    ]
    coupons = [
        ProviderCoupon(
            provider_id=item.provider_coupon_id,
            fingerprint=_fingerprint(
                "coupon",
                (
                    item.provider_coupon_id,
                    item.partner_provider_id,
                    item.title,
                    item.valid_from,
                    item.valid_until,
                    item.activation_status,
                ),
            ),
            title=item.title,
            partner_provider_id=item.partner_provider_id,
            description=item.description,
            valid_from=item.valid_from,
            valid_until=item.valid_until,
            status=item.activation_status,
            multiplier=item.multiplier,
            bonus_points=item.bonus_points,
            condition_text=item.condition_text,
            provider_updated_at=item.provider_updated_at,
        )
        for item in body.coupons
    ]
    return SyncPayload(
        balance=balance,
        expirations=expirations,
        partners=partners,
        activities=activities,
        coupons=coupons,
    )
