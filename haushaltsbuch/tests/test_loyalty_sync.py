from __future__ import annotations

import json
from datetime import date, datetime, timezone

from conftest import PREFIX
from test_loyalty_connections import _create_connection
from test_v1_api import _create_household

from backend.loyalty_models import ProviderCapabilities
from backend.loyalty_provider import (
    AuthRequired,
    ProviderActivity,
    ProviderBalance,
    ProviderCoupon,
    ProviderExpiration,
    ProviderPartner,
    RateLimited,
)
from backend.loyalty_registry import register, unregister
from backend.providers.fake import FakeLoyaltyProvider


def _fake() -> FakeLoyaltyProvider:
    return FakeLoyaltyProvider(
        capabilities=ProviderCapabilities(
            balance=True, expirations=True, activities=True, coupons=True, partners=True
        ),
        balance=ProviderBalance(
            observed_at=datetime(2026, 7, 18, 10, tzinfo=timezone.utc), points=1234
        ),
        expirations=[ProviderExpiration(date(2026, 9, 30), 200)],
        partners=[ProviderPartner("dm", "dm")],
        activities=[
            ProviderActivity("a-1", "fa-1", "earn", date(2026, 7, 17), 50, "dm")
        ],
        coupons=[
            ProviderCoupon("c-1", "fc-1", "10fach", "dm", valid_until=date(2026, 8, 1))
        ],
    )


def _enabled_connection(client, headers, monkeypatch):
    connection = _create_connection(client, headers, monkeypatch).json()
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections "
            "SET feature_enabled=1 WHERE id=?", (connection["id"],)
        )
    return connection


def test_manual_sync_is_idempotent_and_records_history(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    connection = _enabled_connection(client, owner_headers, monkeypatch)
    provider = _fake()
    register(provider)
    try:
        first = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
        )
        provider.activities[0] = ProviderActivity(
            "a-1", "fa-2", "earn", date(2026, 7, 17), 75, "dm"
        )
        provider.coupons[0] = ProviderCoupon(
            "c-1", "fc-2", "15fach", "dm", valid_until=date(2026, 8, 1)
        )
        second = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
        )
    finally:
        unregister("payback")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["run"]["status"] == "succeeded"

    from hydrahive.db.connection import db
    with db() as conn:
        counts = {
            table: conn.execute(
                f"SELECT COUNT(*) FROM module_haushaltsbuch_{table}"
            ).fetchone()[0]
            for table in (
                "loyalty_balances", "loyalty_expirations", "loyalty_partners",
                "loyalty_activities", "loyalty_coupons", "loyalty_sync_runs",
            )
        }
        activity = conn.execute(
            "SELECT fingerprint,points_delta FROM module_haushaltsbuch_loyalty_activities"
        ).fetchone()
        coupon = conn.execute(
            "SELECT fingerprint,title FROM module_haushaltsbuch_loyalty_coupons"
        ).fetchone()
    assert counts == {
        "loyalty_balances": 1, "loyalty_expirations": 1,
        "loyalty_partners": 1, "loyalty_activities": 1,
        "loyalty_coupons": 1, "loyalty_sync_runs": 2,
    }
    assert (activity["fingerprint"], activity["points_delta"]) == ("fa-2", 75)
    assert (coupon["fingerprint"], coupon["title"]) == ("fc-2", "15fach")

    history = client.get(
        f"{PREFIX}/loyalty/connections/{connection['id']}/sync-runs",
        headers=owner_headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert all(item["error_code"] is None for item in history.json())


def test_sync_requires_enabled_registered_provider(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    connection = _create_connection(client, owner_headers, monkeypatch).json()
    disabled = client.post(
        f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
    )
    assert disabled.status_code == 409
    assert disabled.json()["detail"]["code"] == "loyalty_provider_disabled"

    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections SET feature_enabled=1 WHERE id=?",
            (connection["id"],),
        )
    missing = client.post(
        f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
    )
    assert missing.status_code == 503
    assert missing.json()["detail"]["code"] == "loyalty_provider_unavailable"


def test_recent_sync_lock_prevents_parallel_run(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    connection = _enabled_connection(client, owner_headers, monkeypatch)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections SET status='syncing' WHERE id=?",
            (connection["id"],),
        )
        conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_sync_runs"
            "(household_id,connection_id,trigger,status) VALUES(?,?,'manual','running')",
            (connection["household_id"], connection["id"]),
        )
    response = client.post(
        f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "loyalty_sync_running"


def test_stale_sync_lock_is_recovered(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    connection = _enabled_connection(client, owner_headers, monkeypatch)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections SET status='syncing' WHERE id=?",
            (connection["id"],),
        )
        conn.execute(
            "INSERT INTO module_haushaltsbuch_loyalty_sync_runs"
            "(household_id,connection_id,trigger,status,started_at) "
            "VALUES(?,?,'manual','running','2020-01-01T00:00:00Z')",
            (connection["household_id"], connection["id"]),
        )
    register(_fake())
    try:
        response = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
        )
    finally:
        unregister("payback")
    assert response.status_code == 200, response.text
    with db() as conn:
        runs = conn.execute(
            "SELECT status,error_code FROM module_haushaltsbuch_loyalty_sync_runs ORDER BY id"
        ).fetchall()
    assert [(row["status"], row["error_code"]) for row in runs] == [
        ("failed", "stale_sync_recovered"), ("succeeded", None)
    ]


def test_auth_and_rate_limit_failures_are_redacted_and_persisted(
    client, owner_headers, monkeypatch
):
    _create_household(client, owner_headers)
    connection = _enabled_connection(client, owner_headers, monkeypatch)

    provider = _fake()
    provider.fail_next("probe", AuthRequired())
    register(provider)
    try:
        auth = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
        )
    finally:
        unregister("payback")
    assert auth.status_code == 409
    assert auth.json()["detail"]["code"] == "loyalty_reauth_required"

    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            "UPDATE module_haushaltsbuch_loyalty_connections "
            "SET status='active' WHERE id=?", (connection["id"],)
        )
    provider = _fake()
    provider.fail_next("probe", RateLimited(120))
    register(provider)
    try:
        limited = client.post(
            f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
        )
    finally:
        unregister("payback")
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "loyalty_rate_limited"
    cooldown = client.post(
        f"{PREFIX}/loyalty/connections/{connection['id']}/sync", headers=owner_headers
    )
    assert cooldown.status_code == 429
    assert cooldown.json()["detail"]["code"] == "loyalty_rate_limited"

    with db() as conn:
        runs = conn.execute(
            "SELECT error_code,next_allowed_attempt_at FROM "
            "module_haushaltsbuch_loyalty_sync_runs ORDER BY id"
        ).fetchall()
        dump = json.dumps([dict(row) for row in runs])
    assert [row["error_code"] for row in runs] == ["auth_required", "rate_limited"]
    assert runs[-1]["next_allowed_attempt_at"] is not None
    assert "super-secret" not in dump
