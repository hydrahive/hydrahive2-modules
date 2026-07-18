from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib

from backend.loyalty_models import ProviderCapabilities
from backend.loyalty_receipt_models import (
    ProviderReceipt,
    ProviderReceiptAdjustment,
    ProviderReceiptItem,
)
from backend.loyalty_registry import register, unregister
from backend.providers.fake import FakeLoyaltyProvider
from conftest import PREFIX
from hydrahive.credentials.models import Credential
from hydrahive.credentials.store import save_credential
from hydrahive.db.connection import db
from test_v1_api import _create_household


def _receipt(name: str = "Milch") -> ProviderReceipt:
    return ProviderReceipt(
        provider_id="ticket-1",
        fingerprint="ignored-provider-fingerprint",
        merchant_name="Lidl",
        content_hash=hashlib.sha256(name.encode()).hexdigest(),
        purchased_at=datetime(2026, 7, 18, 12, 30, tzinfo=timezone.utc),
        store_id="DE-1",
        store_name="Lidl Berlin",
        store_address="Teststraße 1",
        total_minor=499,
        currency="EUR",
        total_discount_minor=50,
        items=[ProviderReceiptItem(0, name, None, "1", "piece", 249, 249, "A")],
        adjustments=[ProviderReceiptAdjustment("discount", -50, "Rabatt", 0)],
    )


def _connection(client, headers) -> dict:
    assert save_credential(
        "owner", Credential("lidl-test", "bearer", "refresh-token")
    )[0]
    response = client.post(
        f"{PREFIX}/loyalty/connections",
        headers=headers,
        json={
            "provider": "lidl_plus",
            "credential_ref": "lidl-test",
            "provider_account_id": "account-1",
            "masked_account": "Lidl Plus",
            "country_code": "DE",
            "language_code": "de",
        },
    )
    assert response.status_code == 201, response.text
    connection = response.json()
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections "
            "SET feature_enabled=1 WHERE id=?",
            (connection["id"],),
        )
    return connection


def test_legacy_generic_reauth_state_can_recover_once(client, owner_headers):
    _create_household(client, owner_headers)
    connection = _connection(client, owner_headers)
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections "
            "SET status='reauth_required',last_error_code='auth_required' WHERE id=?",
            (connection["id"],),
        )
    provider = FakeLoyaltyProvider(
        provider_id="lidl_plus",
        capabilities=ProviderCapabilities(receipts=True),
        receipts=[],
    )
    register(provider)
    try:
        recovered = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync",
            headers=owner_headers,
        )
        with db() as conn:
            conn.execute(
                "UPDATE module_haushaltsbuch_loyalty_connections SET "
                "status='reauth_required',last_error_code='lidl_refresh_rejected' "
                "WHERE id=?", (connection["id"],),
            )
        precise_reauth = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync",
            headers=owner_headers,
        )
    finally:
        unregister("lidl_plus")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["connection"]["status"] == "active"
    assert recovered.json()["connection"]["last_error_code"] is None
    assert precise_reauth.status_code == 409
    assert precise_reauth.json()["detail"]["code"] == "loyalty_reauth_required"


def test_receipt_sync_is_idempotent_and_exposes_scoped_details(
    client, owner_headers, outsider_headers
):
    _create_household(client, owner_headers)
    connection = _connection(client, owner_headers)
    provider = FakeLoyaltyProvider(
        provider_id="lidl_plus",
        capabilities=ProviderCapabilities(
            receipts=True, receipt_items=True, discounts=True, deposits=True
        ),
        receipts=[_receipt()],
    )
    register(provider)
    try:
        first = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync",
            headers=owner_headers,
        )
        provider.receipts[0] = replace(
            _receipt("Haferdrink"),
            content_hash=hashlib.sha256(b"changed-content").hexdigest()
        )
        second = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync",
            headers=owner_headers,
        )
    finally:
        unregister("lidl_plus")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    listed = client.get(f"{PREFIX}/loyalty/receipts", headers=owner_headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    assert listed.json()[0]["store_name"] == "Lidl Berlin"
    receipt_id = listed.json()[0]["id"]

    detail = client.get(
        f"{PREFIX}/loyalty/receipts/{receipt_id}", headers=owner_headers
    )
    assert detail.status_code == 200, detail.text
    assert [item["original_name"] for item in detail.json()["items"]] == [
        "Haferdrink"
    ]
    assert detail.json()["adjustments"][0]["item_id"] == detail.json()["items"][0]["id"]
    assert "content_hash" not in detail.json()
    assert "provider_fingerprint" not in detail.json()

    hidden = client.get(
        f"{PREFIX}/loyalty/receipts/{receipt_id}", headers=outsider_headers
    )
    assert hidden.status_code in (403, 404)

    with db() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM module_haushaltsbuch_loyalty_receipts"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM module_haushaltsbuch_loyalty_receipt_items"
        ).fetchone()[0] == 1
        fingerprint = conn.execute(
            "SELECT provider_fingerprint FROM module_haushaltsbuch_loyalty_receipts"
        ).fetchone()[0]
    assert len(fingerprint) == 64
    assert fingerprint != _receipt().fingerprint
