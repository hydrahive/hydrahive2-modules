from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATIONS = Path(__file__).parents[1] / "migrations"


def test_removal_migration_deletes_only_browser_bridge_connections():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    for name in (
        "001_household_core.sql",
        "004_loyalty_foundation.sql",
        "007_payback_browser_bridge.sql",
    ):
        conn.executescript((MIGRATIONS / name).read_text())
    conn.execute(
        "INSERT INTO module_haushaltsbuch_households"
        "(id,name,base_currency,timezone,owner_user_id) VALUES(1,'Test','EUR','UTC','u1')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_members"
        "(id,household_id,user_id,username,role) VALUES(1,1,'u1','owner','owner')"
    )
    connection_values = (
        1,
        "payback",
        1,
        "payback-browser-bridge",
        "bridge-account",
        "PAYBACK Browser-Bridge",
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_loyalty_connections"
        "(id,household_id,provider,owner_member_id,credential_ref,"
        "account_fingerprint,masked_account) VALUES(1,?,?,?,?,?,?)",
        connection_values,
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_loyalty_connections"
        "(id,household_id,provider,owner_member_id,credential_ref,"
        "account_fingerprint,masked_account) "
        "VALUES(2,1,'payback',1,'manual-reference','manual-account','PAYBACK manuell')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_payback_bridge_flows"
        "(flow_id,code_hmac,household_id,member_id,visibility,expires_at,"
        "consumed_at,connection_id) VALUES(?,?,?,?,?,?,?,?)",
        ("f" * 32, "a" * 64, 1, 1, "owner", "2026-07-19T12:00:00+00:00", "now", 1),
    )

    conn.executescript(
        (MIGRATIONS / "008_remove_payback_browser_bridge.sql").read_text()
    )

    remaining = conn.execute(
        "SELECT id,credential_ref FROM module_haushaltsbuch_loyalty_connections ORDER BY id"
    ).fetchall()
    flow_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='module_haushaltsbuch_payback_bridge_flows'"
    ).fetchone()
    assert remaining == [(2, "manual-reference")]
    assert flow_table is None
