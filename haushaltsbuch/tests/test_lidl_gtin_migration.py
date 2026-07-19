from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations" / "006_optional_gtin.sql"


def test_migration_reclassifies_only_valid_arrays_with_info_warnings():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE module_haushaltsbuch_loyalty_receipts "
        "(id INTEGER PRIMARY KEY, validation_status TEXT NOT NULL, warnings_json TEXT NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO module_haushaltsbuch_loyalty_receipts VALUES(?,?,?)",
        [
            (1, "needs_review", '["invalid_gtin","timezone_inferred_de"]'),
            (2, "needs_review", '["invalid_gtin","missing_total"]'),
            (3, "needs_review", '["missing_total"]'),
            (4, "needs_review", '"invalid_gtin"'),
            (5, "needs_review", '["invalid_gtin",null]'),
        ],
    )

    conn.executescript(MIGRATION.read_text())
    statuses = dict(conn.execute(
        "SELECT id,validation_status FROM module_haushaltsbuch_loyalty_receipts"
    ).fetchall())

    assert statuses == {
        1: "valid",
        2: "needs_review",
        3: "needs_review",
        4: "needs_review",
        5: "needs_review",
    }
