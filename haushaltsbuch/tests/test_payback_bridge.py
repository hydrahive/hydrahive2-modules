from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
import pytest

from backend.payback_bridge_models import PaybackBridgeImport
from conftest import PREFIX
from test_v1_api import _create_household


def _start(client, headers, **overrides):
    return client.post(
        f"{PREFIX}/loyalty/payback/bridge/start",
        headers=headers,
        json={
            "accepted_experimental_risk": True,
            "alias": "PAYBACK",
            "visibility": "owner",
            **overrides,
        },
    )


def _payload(code: str) -> dict:
    return {
        "pairing_code": code,
        "captured_at": "2026-07-18T12:00:00Z",
        "balance": {"observed_at": "2026-07-18T12:00:00Z", "available_points": 1234},
        "expirations": [
            {"expiration_date": "2026-09-30", "points": 200, "status": "scheduled"}
        ],
        "partners": [{"provider_partner_id": "dm", "name": "dm", "active": True}],
        "activities": [
            {
                "provider_activity_id": "a-1",
                "activity_type": "earn",
                "activity_date": "2026-07-17",
                "points_delta": 120,
                "partner_provider_id": "dm",
                "original_description": "Einkauf",
                "purchase_amount_minor": 4599,
                "purchase_currency": "EUR",
            }
        ],
        "coupons": [
            {
                "provider_coupon_id": "c-1",
                "partner_provider_id": "dm",
                "title": "10fach Punkte",
                "valid_until": "2026-08-01",
                "activation_status": "available",
                "multiplier": "10",
            }
        ],
    }


def test_import_schema_forbids_unknown_fields_and_enforces_limits():
    payload = _payload("a" * 43)
    payload["raw_html"] = "<html>secret</html>"
    with pytest.raises(ValidationError):
        PaybackBridgeImport.model_validate(payload)

    payload = _payload("a" * 43)
    payload["activities"] = payload["activities"] * 2001
    with pytest.raises(ValidationError):
        PaybackBridgeImport.model_validate(payload)


def test_public_import_hides_schema_details_and_enforces_body_bound(client):
    invalid = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import",
        json={"pairing_code": "x" * 43, "raw_html": "secret"},
    )
    oversized = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "20000000"},
    )
    for response in (invalid, oversized):
        assert response.status_code == 404
        assert response.json() == {"detail": {"code": "payback_bridge_import_invalid"}}


def test_public_import_is_rate_limited_before_body_parsing(client, monkeypatch):
    monkeypatch.setattr(
        "backend.routes_loyalty.check_rate", lambda *args, **kwargs: (False, 12)
    )

    response = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import",
        content=b"not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "12"
    assert response.json()["detail"] == {"code": "payback_bridge_rate_limited"}


def test_public_import_rejects_timestamps_without_timezone(client, owner_headers):
    _create_household(client, owner_headers)
    flow = _start(client, owner_headers).json()
    payloads = []
    for path in (
        ("captured_at",),
        ("balance", "observed_at"),
        ("activities", 0, "provider_updated_at"),
        ("coupons", 0, "provider_updated_at"),
    ):
        payload = _payload(flow["pairing_code"])
        target = payload
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = "2026-07-19T10:00:00"
        payloads.append(payload)

    for payload in payloads:
        response = client.post(f"{PREFIX}/loyalty/payback/bridge/import", json=payload)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "payback_bridge_import_invalid"


def test_start_requires_auth_risk_acceptance_and_stores_only_hmac(
    client, owner_headers
):
    _create_household(client, owner_headers)
    assert _start(client, {}).status_code == 401
    rejected = _start(client, owner_headers, accepted_experimental_risk=False)
    assert rejected.status_code == 422

    response = _start(client, owner_headers)
    assert response.status_code == 201, response.text
    result = response.json()
    assert len(result["pairing_code"]) >= 43
    assert result["import_path"].endswith("/loyalty/payback/bridge/import")

    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM module_haushaltsbuch_payback_bridge_flows WHERE flow_id=?",
            (result["flow_id"],),
        ).fetchone()
    assert row["code_hmac"] != result["pairing_code"]
    assert result["pairing_code"] not in "|".join(str(value) for value in row)
    assert len(row["code_hmac"]) == 64


def test_public_import_consumes_code_once_and_is_idempotent_across_flows(
    client, owner_headers
):
    _create_household(client, owner_headers)
    first_flow = _start(client, owner_headers).json()
    first = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import",
        json=_payload(first_flow["pairing_code"]),
    )
    assert first.status_code == 200, first.text
    assert first.json()["counts"]["fetched"] == 5
    assert "connection" not in first.json()
    status_result = client.get(
        f"{PREFIX}/loyalty/payback/bridge/status/{first_flow['flow_id']}",
        headers=owner_headers,
    ).json()
    connection_id = status_result["connection"]["id"]

    replay = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import",
        json=_payload(first_flow["pairing_code"]),
    )
    assert replay.status_code == 404
    assert replay.json()["detail"] == {"code": "payback_bridge_import_invalid"}

    second_flow = _start(client, owner_headers).json()
    second = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import",
        json=_payload(second_flow["pairing_code"]),
    )
    assert second.status_code == 200, second.text
    second_status = client.get(
        f"{PREFIX}/loyalty/payback/bridge/status/{second_flow['flow_id']}",
        headers=owner_headers,
    ).json()
    assert second_status["connection"]["id"] == connection_id

    from hydrahive.db.connection import db

    with db() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM module_haushaltsbuch_loyalty_activities"
            ).fetchone()[0]
            == 1
        )
        activity = conn.execute(
            "SELECT purchase_amount_minor,purchase_currency "
            "FROM module_haushaltsbuch_loyalty_activities"
        ).fetchone()
    assert tuple(activity) == (4599, "EUR")


def test_invalid_expired_and_consumed_codes_share_generic_error(client, owner_headers):
    _create_household(client, owner_headers)
    flow = _start(client, owner_headers).json()

    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_payback_bridge_flows SET expires_at=? WHERE flow_id=?",
            (
                (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                flow["flow_id"],
            ),
        )

    expired = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import", json=_payload(flow["pairing_code"])
    )
    wrong = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import", json=_payload("x" * 43)
    )
    assert expired.status_code == wrong.status_code == 404
    assert (
        expired.json()
        == wrong.json()
        == {"detail": {"code": "payback_bridge_import_invalid"}}
    )


def test_flow_status_is_bound_to_creating_member(client, owner_headers, member_headers):
    _create_household(client, owner_headers)
    client.post(
        f"{PREFIX}/household/members",
        headers=owner_headers,
        json={"username": "member"},
    )
    flow = _start(client, member_headers).json()

    hidden = client.get(
        f"{PREFIX}/loyalty/payback/bridge/status/{flow['flow_id']}",
        headers=owner_headers,
    )
    visible = client.get(
        f"{PREFIX}/loyalty/payback/bridge/status/{flow['flow_id']}",
        headers=member_headers,
    )
    assert hidden.status_code == 404
    assert visible.json()["status"] == "pending"
