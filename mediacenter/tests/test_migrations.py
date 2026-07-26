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
    assert names == {"module_mediacenter_jobs", "module_mediacenter_audit"}
