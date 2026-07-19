from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations" / "007_payback_browser_bridge.sql"


def test_migration_adds_purchase_fields_and_hmac_only_flow_table():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE module_haushaltsbuch_households(id INTEGER PRIMARY KEY);
        CREATE TABLE module_haushaltsbuch_members(
          id INTEGER PRIMARY KEY, household_id INTEGER NOT NULL,
          UNIQUE(id, household_id)
        );
        CREATE TABLE module_haushaltsbuch_loyalty_connections(
          id INTEGER PRIMARY KEY, household_id INTEGER NOT NULL,
          UNIQUE(id, household_id)
        );
        CREATE TABLE module_haushaltsbuch_loyalty_activities(id INTEGER PRIMARY KEY);
        """
    )
    conn.executescript(MIGRATION.read_text())

    activity_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(module_haushaltsbuch_loyalty_activities)"
        )
    }
    flow_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(module_haushaltsbuch_payback_bridge_flows)"
        )
    }
    assert {"purchase_amount_minor", "purchase_currency"} <= activity_columns
    assert "code_hmac" in flow_columns
    assert not ({"pairing_code", "code", "token", "raw_html"} & flow_columns)
