from __future__ import annotations

import json
import sqlite3
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = MODULE_ROOT / "tests" / "fixtures" / "legacy_v040_inventory.json"


def _columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def test_legacy_v040_schema_matches_frozen_inventory() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        (MODULE_ROOT / "migrations" / "001_zerlegewerkstatt.sql").read_text(encoding="utf-8")
    )

    actual = {
        table: _columns(connection, table)
        for table in contract["tables"]
    }
    indexes = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex_%' ORDER BY name"
        )
    ]

    assert contract["contract"] == "zerlegewerkstatt-legacy-v0.4.0"
    assert actual == contract["tables"]
    assert indexes == sorted(contract["indexes"])


def test_legacy_v040_data_root_stays_outside_module_installation() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["data_root"] == "zerlegewerkstatt/cases/<case-id>"

    from hydrahive.settings import settings

    from backend.files import cases_root

    root = cases_root("legacy-0001")
    assert root == settings.data_dir / "zerlegewerkstatt" / "cases" / "legacy-0001"
    assert settings.modules_dir not in root.parents
