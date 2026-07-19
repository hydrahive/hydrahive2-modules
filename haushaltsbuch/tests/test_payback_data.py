from __future__ import annotations

from conftest import PREFIX
from test_payback_bridge import _payload, _start
from test_v1_api import _create_household


def _import(client, headers, *, visibility="owner") -> int:
    flow = _start(client, headers, visibility=visibility).json()
    response = client.post(
        f"{PREFIX}/loyalty/payback/bridge/import", json=_payload(flow["pairing_code"])
    )
    assert response.status_code == 200, response.text
    status = client.get(
        f"{PREFIX}/loyalty/payback/bridge/status/{flow['flow_id']}", headers=headers
    )
    assert status.status_code == 200, status.text
    return status.json()["connection"]["id"]


def test_data_endpoint_returns_bounded_data_and_metrics(client, owner_headers):
    _create_household(client, owner_headers)
    connection_id = _import(client, owner_headers)
    from hydrahive.db.connection import db

    with db(immediate=True) as conn:
        household_id = conn.execute(
            "SELECT household_id FROM module_haushaltsbuch_loyalty_connections WHERE id=?",
            (connection_id,),
        ).fetchone()[0]
        for fingerprint, activity_type, points in (
            ("expired-points", "expire", -50),
            ("positive-reversal", "reversal", 20),
        ):
            conn.execute(
                "INSERT INTO module_haushaltsbuch_loyalty_activities"
                "(household_id,connection_id,fingerprint,activity_type,activity_date,points_delta) "
                "VALUES(?,?,?,?,?,?)",
                (
                    household_id,
                    connection_id,
                    fingerprint,
                    activity_type,
                    "2026-01-01",
                    points,
                ),
            )

    response = client.get(
        f"{PREFIX}/loyalty/payback/connections/{connection_id}/data",
        headers=owner_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["latest_balance"]["available_points"] == 1234
    assert data["metrics"]["activity_count"] == 3
    assert data["metrics"]["points_collected"] == 120
    assert data["metrics"]["points_redeemed"] == 0
    assert data["metrics"]["purchase_totals"] == [
        {"currency": "EUR", "amount_minor": 4599, "activity_count": 1}
    ]
    assert data["metrics"]["coupon_status"] == {"available": 1}
    assert data["activities"][0]["purchase_amount_minor"] == 4599
    assert "credential_ref" not in response.text


def test_private_and_household_visibility_are_enforced(
    client, owner_headers, member_headers, outsider_headers
):
    _create_household(client, owner_headers)
    client.post(
        f"{PREFIX}/household/members",
        headers=owner_headers,
        json={"username": "member"},
    )
    private_id = _import(client, member_headers, visibility="owner")

    assert (
        client.get(
            f"{PREFIX}/loyalty/payback/connections/{private_id}/data",
            headers=outsider_headers,
        ).status_code
        == 404
    )
    # Existing loyalty visibility semantics allow the household owner to administer all.
    assert (
        client.get(
            f"{PREFIX}/loyalty/payback/connections/{private_id}/data",
            headers=owner_headers,
        ).status_code
        == 200
    )

    shared_id = _import(client, owner_headers, visibility="household")
    assert (
        client.get(
            f"{PREFIX}/loyalty/payback/connections/{shared_id}/data",
            headers=member_headers,
        ).status_code
        == 200
    )
