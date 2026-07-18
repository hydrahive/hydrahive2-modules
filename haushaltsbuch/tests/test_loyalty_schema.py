from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

MODULE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = MODULE_DIR / "migrations"

LOYALTY_TABLES = {
    "module_haushaltsbuch_loyalty_connections",
    "module_haushaltsbuch_loyalty_sync_runs",
    "module_haushaltsbuch_loyalty_balances",
    "module_haushaltsbuch_loyalty_activities",
    "module_haushaltsbuch_loyalty_expirations",
    "module_haushaltsbuch_loyalty_partners",
    "module_haushaltsbuch_loyalty_coupons",
}


@pytest.fixture
def loyalty_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((MIGRATIONS_DIR / "001_household_core.sql").read_text())
    migration = (MIGRATIONS_DIR / "004_loyalty_foundation.sql").read_text()
    conn.executescript(migration)
    conn.executescript(migration)
    yield conn
    conn.close()


def _household(conn: sqlite3.Connection, name: str, owner: str) -> int:
    return conn.execute(
        """
        INSERT INTO module_haushaltsbuch_households
          (name, base_currency, timezone, owner_user_id)
        VALUES (?, 'EUR', 'Europe/Berlin', ?)
        """,
        (name, owner),
    ).lastrowid


def _member(conn: sqlite3.Connection, household_id: int, user_id: str) -> int:
    return conn.execute(
        """
        INSERT INTO module_haushaltsbuch_members
          (household_id, user_id, username, role)
        VALUES (?, ?, ?, 'owner')
        """,
        (household_id, user_id, user_id),
    ).lastrowid


def _connection(
    conn: sqlite3.Connection,
    household_id: int,
    member_id: int,
    *,
    fingerprint: str = "account-fingerprint",
    provider: str = "payback",
) -> int:
    return conn.execute(
        """
        INSERT INTO module_haushaltsbuch_loyalty_connections
          (household_id, provider, owner_member_id, credential_ref,
           account_fingerprint, masked_account, capabilities_json)
        VALUES (?, ?, ?, 'credential:test', ?, '****1234', '{}')
        """,
        (household_id, provider, member_id, fingerprint),
    ).lastrowid


def test_migration_is_idempotent_and_creates_foundation_tables(loyalty_db):
    tables = {
        row[0]
        for row in loyalty_db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert LOYALTY_TABLES <= tables


def test_connection_enforces_household_member_scope_and_identity(loyalty_db):
    first_household = _household(loyalty_db, "First", "owner-1")
    second_household = _household(loyalty_db, "Second", "owner-2")
    member_id = _member(loyalty_db, first_household, "member-1")
    _connection(loyalty_db, first_household, member_id)

    with pytest.raises(sqlite3.IntegrityError):
        _connection(loyalty_db, second_household, member_id, fingerprint="other")
    with pytest.raises(sqlite3.IntegrityError):
        _connection(loyalty_db, first_household, member_id)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("provider", "unknown"),
        ("visibility", "public"),
        ("status", "connected"),
        ("feature_enabled", 2),
        ("sync_enabled", -1),
        ("revision", 0),
    ],
)
def test_connection_checks_reject_invalid_values(loyalty_db, column, value):
    household_id = _household(loyalty_db, "Checks", "checks-owner")
    member_id = _member(loyalty_db, household_id, "checks-member")

    values = {
        "household_id": household_id,
        "provider": "payback",
        "owner_member_id": member_id,
        "credential_ref": "credential:test",
        "account_fingerprint": "fingerprint",
        "masked_account": "****1234",
        "capabilities_json": "{}",
        column: value,
    }
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    with pytest.raises(sqlite3.IntegrityError):
        loyalty_db.execute(
            f"INSERT INTO module_haushaltsbuch_loyalty_connections "
            f"({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        )


def test_connection_children_cannot_cross_household_scope(loyalty_db):
    first_household = _household(loyalty_db, "First", "scope-owner-1")
    second_household = _household(loyalty_db, "Second", "scope-owner-2")
    member_id = _member(loyalty_db, first_household, "scope-member")
    connection_id = _connection(loyalty_db, first_household, member_id)

    child_inserts = [
        (
            "module_haushaltsbuch_loyalty_sync_runs",
            "household_id, connection_id, trigger, status",
            (second_household, connection_id, "manual", "running"),
        ),
        (
            "module_haushaltsbuch_loyalty_balances",
            "household_id, connection_id, observed_at, available_points, fingerprint",
            (second_household, connection_id, "2026-07-18", 100, "balance-1"),
        ),
        (
            "module_haushaltsbuch_loyalty_activities",
            "household_id, connection_id, fingerprint, activity_type, activity_date, points_delta",
            (second_household, connection_id, "activity-1", "earn", "2026-07-18", 10),
        ),
        (
            "module_haushaltsbuch_loyalty_expirations",
            "household_id, connection_id, expiration_date, points, status",
            (second_household, connection_id, "2026-12-31", 10, "scheduled"),
        ),
        (
            "module_haushaltsbuch_loyalty_coupons",
            "household_id, connection_id, fingerprint, title, activation_status, remote_status",
            (second_household, connection_id, "coupon-1", "Coupon", "available", "active"),
        ),
    ]
    for table, columns, values in child_inserts:
        placeholders = ", ".join("?" for _ in values)
        with pytest.raises(sqlite3.IntegrityError):
            loyalty_db.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values
            )


def test_sync_run_checks_status_counters_and_time_order(loyalty_db):
    household_id = _household(loyalty_db, "Sync", "sync-owner")
    member_id = _member(loyalty_db, household_id, "sync-member")
    connection_id = _connection(loyalty_db, household_id, member_id)

    invalid_rows = [
        ("automatic", "running", None, 0),
        ("manual", "unknown", None, 0),
        ("manual", "succeeded", "2026-07-17T00:00:00Z", 0),
        ("manual", "failed", None, -1),
    ]
    for trigger, status, finished_at, fetched_count in invalid_rows:
        with pytest.raises(sqlite3.IntegrityError):
            loyalty_db.execute(
                """
                INSERT INTO module_haushaltsbuch_loyalty_sync_runs
                  (household_id, connection_id, trigger, started_at, finished_at,
                   status, fetched_count)
                VALUES (?, ?, ?, '2026-07-18T00:00:00Z', ?, ?, ?)
                """,
                (household_id, connection_id, trigger, finished_at, status, fetched_count),
            )


def test_loyalty_data_is_idempotent_and_partner_scoped(loyalty_db):
    household_id = _household(loyalty_db, "Data", "data-owner")
    other_household = _household(loyalty_db, "Other", "data-owner-2")
    member_id = _member(loyalty_db, household_id, "data-member")
    connection_id = _connection(loyalty_db, household_id, member_id)

    loyalty_db.execute(
        """
        INSERT INTO module_haushaltsbuch_loyalty_balances
          (household_id, connection_id, observed_at, available_points, fingerprint)
        VALUES (?, ?, '2026-07-18T10:00:00Z', 1200, 'balance-fingerprint')
        """,
        (household_id, connection_id),
    )
    loyalty_db.execute(
        """
        INSERT INTO module_haushaltsbuch_loyalty_activities
          (household_id, connection_id, provider_activity_id, fingerprint,
           activity_type, activity_date, points_delta)
        VALUES (?, ?, 'remote-activity', 'activity-fingerprint', 'earn', '2026-07-18', 100)
        """,
        (household_id, connection_id),
    )
    partner_id = loyalty_db.execute(
        """
        INSERT INTO module_haushaltsbuch_loyalty_partners
          (household_id, provider, provider_partner_id, name)
        VALUES (?, 'payback', 'partner-1', 'Partner')
        """,
        (household_id,),
    ).lastrowid
    loyalty_db.execute(
        """
        INSERT INTO module_haushaltsbuch_loyalty_coupons
          (household_id, connection_id, provider_coupon_id, fingerprint,
           partner_id, title, activation_status, remote_status)
        VALUES (?, ?, 'remote-coupon', 'coupon-fingerprint', ?, 'Coupon',
                'available', 'active')
        """,
        (household_id, connection_id, partner_id),
    )

    duplicate_statements = [
        (
            "INSERT INTO module_haushaltsbuch_loyalty_balances "
            "(household_id, connection_id, observed_at, available_points, fingerprint) "
            "VALUES (?, ?, '2026-07-18T11:00:00Z', 1200, 'balance-fingerprint')",
            (household_id, connection_id),
        ),
        (
            "INSERT INTO module_haushaltsbuch_loyalty_activities "
            "(household_id, connection_id, provider_activity_id, fingerprint, activity_type, activity_date, points_delta) "
            "VALUES (?, ?, 'remote-activity', 'other-fingerprint', 'earn', '2026-07-18', 100)",
            (household_id, connection_id),
        ),
        (
            "INSERT INTO module_haushaltsbuch_loyalty_partners "
            "(household_id, provider, provider_partner_id, name) "
            "VALUES (?, 'payback', 'partner-1', 'Duplicate')",
            (household_id,),
        ),
        (
            "INSERT INTO module_haushaltsbuch_loyalty_coupons "
            "(household_id, connection_id, provider_coupon_id, fingerprint, title, activation_status, remote_status) "
            "VALUES (?, ?, 'remote-coupon', 'other-coupon-fingerprint', 'Duplicate', 'available', 'active')",
            (household_id, connection_id),
        ),
    ]
    for statement, parameters in duplicate_statements:
        with pytest.raises(sqlite3.IntegrityError):
            loyalty_db.execute(statement, parameters)

    with pytest.raises(sqlite3.IntegrityError):
        loyalty_db.execute(
            """
            INSERT INTO module_haushaltsbuch_loyalty_coupons
              (household_id, connection_id, fingerprint, partner_id, title,
               activation_status, remote_status)
            VALUES (?, ?, 'cross-scope-coupon', ?, 'Invalid', 'available', 'active')
            """,
            (other_household, connection_id, partner_id),
        )


def test_value_checks_reject_invalid_points_dates_and_valuation_pairs(loyalty_db):
    household_id = _household(loyalty_db, "Values", "values-owner")
    member_id = _member(loyalty_db, household_id, "values-member")
    connection_id = _connection(loyalty_db, household_id, member_id)

    invalid_statements = [
        (
            "INSERT INTO module_haushaltsbuch_loyalty_balances "
            "(household_id, connection_id, observed_at, available_points, fingerprint) "
            "VALUES (?, ?, '2026-07-18', -1, 'negative')"
        ),
        (
            "INSERT INTO module_haushaltsbuch_loyalty_balances "
            "(household_id, connection_id, observed_at, available_points, money_value_minor, fingerprint) "
            "VALUES (?, ?, '2026-07-18', 1, 1, 'incomplete-valuation')"
        ),
        (
            "INSERT INTO module_haushaltsbuch_loyalty_expirations "
            "(household_id, connection_id, expiration_date, points, status) "
            "VALUES (?, ?, '2026-12-31', 0, 'scheduled')"
        ),
        (
            "INSERT INTO module_haushaltsbuch_loyalty_coupons "
            "(household_id, connection_id, fingerprint, title, valid_from, valid_until, activation_status, remote_status) "
            "VALUES (?, ?, 'bad-dates', 'Coupon', '2026-12-31', '2026-01-01', 'available', 'active')"
        ),
    ]
    for statement in invalid_statements:
        with pytest.raises(sqlite3.IntegrityError):
            loyalty_db.execute(statement, (household_id, connection_id))


def test_domain_models_validate_provider_neutral_records():
    from backend.loyalty_models import (
        LoyaltyActivity,
        LoyaltyBalance,
        LoyaltyConnection,
        LoyaltyCoupon,
        LoyaltyExpiration,
        LoyaltyPartner,
        LoyaltySyncRun,
        ProviderCapabilities,
    )

    now = datetime.now(timezone.utc)
    capabilities = ProviderCapabilities(balance=True, activities=True, partners=True)
    connection = LoyaltyConnection(
        id=1,
        household_id=2,
        provider="payback",
        owner_member_id=3,
        credential_ref="credential:test",
        account_fingerprint="fingerprint",
        masked_account="****1234",
        capabilities=capabilities,
    )
    balance = LoyaltyBalance(
        id=1,
        household_id=2,
        connection_id=1,
        observed_at=now,
        available_points=100,
        fingerprint="balance",
    )
    activity = LoyaltyActivity(
        id=1,
        household_id=2,
        connection_id=1,
        fingerprint="activity",
        activity_type="earn",
        activity_date=date.today(),
        points_delta=100,
    )
    expiration = LoyaltyExpiration(
        id=1,
        household_id=2,
        connection_id=1,
        expiration_date=date.today(),
        points=100,
    )
    partner = LoyaltyPartner(
        id=1,
        household_id=2,
        provider="payback",
        provider_partner_id="partner",
        name="Partner",
    )
    coupon = LoyaltyCoupon(
        id=1,
        household_id=2,
        connection_id=1,
        fingerprint="coupon",
        title="Coupon",
    )
    sync_run = LoyaltySyncRun(
        id=1,
        household_id=2,
        connection_id=1,
        trigger="manual",
        started_at=now,
    )

    assert connection.capabilities.balance is True
    assert balance.available_points == activity.points_delta == expiration.points
    assert partner.provider == "payback"
    assert coupon.activation_status == "available"
    assert sync_run.status == "running"

    with pytest.raises(ValidationError):
        LoyaltyCoupon(
            id=2,
            household_id=2,
            connection_id=1,
            fingerprint="invalid",
            title="Invalid",
            valid_from=date(2026, 12, 31),
            valid_until=date(2026, 1, 1),
        )
