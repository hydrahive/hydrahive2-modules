from __future__ import annotations

from hydrahive.db.connection import db
from hydrahive.modules.migrations import apply_module_migrations

from conftest import MODULE_DIR


def test_module_migrations_are_idempotent_and_prefixed():
    apply_module_migrations("mediacenter", MODULE_DIR / "migrations")
    apply_module_migrations("mediacenter", MODULE_DIR / "migrations")
    with db() as conn:
        names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'module_mediacenter_%'"
            ).fetchall()
        }
    assert names == {
        "module_mediacenter_jobs",
        "module_mediacenter_audit",
        "module_mediacenter_action_grants",
        "module_mediacenter_results",
    }


def test_results_migration_repairs_partial_table_before_marking_complete():
    with db() as conn:
        conn.execute("DROP INDEX IF EXISTS idx_mediacenter_results_owner_expiry")
        conn.execute("DROP INDEX IF EXISTS idx_mediacenter_results_claim_expiry")
        conn.execute(
            "DELETE FROM module_schema_version WHERE module_id = ? AND version = 4",
            ("mediacenter",),
        )
        conn.commit()

    apply_module_migrations("mediacenter", MODULE_DIR / "migrations")

    with db() as conn:
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND tbl_name = 'module_mediacenter_results'"
            ).fetchall()
        }
        version = conn.execute(
            "SELECT 1 FROM module_schema_version "
            "WHERE module_id = ? AND version = 4",
            ("mediacenter",),
        ).fetchone()
    assert "idx_mediacenter_results_owner_expiry" in indexes
    assert "idx_mediacenter_results_claim_expiry" in indexes
    assert version is not None
