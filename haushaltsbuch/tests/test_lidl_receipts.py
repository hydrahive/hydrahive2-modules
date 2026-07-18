from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.loyalty_models import ProviderCapabilities
from backend.loyalty_provider import ProviderConnection
from backend.loyalty_receipt_models import ProviderReceipt, ProviderReceiptAdjustment, ProviderReceiptItem
from backend.providers.fake import FakeLoyaltyProvider

MODULE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def receipt_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    for name in ("001_household_core.sql", "004_loyalty_foundation.sql", "005_lidl_receipts.sql"):
        sql = (MODULE_DIR / "migrations" / name).read_text()
        conn.executescript(sql)
        if name == "005_lidl_receipts.sql":
            conn.executescript(sql)
    yield conn
    conn.close()


def test_migration_creates_receipt_and_replay_tables(receipt_db):
    tables = {row[0] for row in receipt_db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "module_haushaltsbuch_loyalty_auth_flows",
        "module_haushaltsbuch_loyalty_receipts",
        "module_haushaltsbuch_loyalty_receipt_items",
        "module_haushaltsbuch_loyalty_receipt_adjustments",
    } <= tables
    columns = {
        row[1] for row in receipt_db.execute(
            "PRAGMA table_info(module_haushaltsbuch_loyalty_auth_flows)"
        )
    }
    assert "flow_id_hash" in columns
    assert {"code", "verifier", "token", "raw_payload"}.isdisjoint(columns)


def _receipt() -> ProviderReceipt:
    return ProviderReceipt(
        provider_id="ticket-1",
        fingerprint="fp-1",
        purchased_at=datetime(2026, 7, 18, 12, 30, tzinfo=timezone.utc),
        merchant_name="Lidl",
        store_name="Lidl Berlin",
        total_minor=499,
        currency="EUR",
        total_discount_minor=50,
        content_hash="hash-1",
        items=[ProviderReceiptItem(0, "Milch", "4001234567899", "1", "piece", 249, 249, "A")],
        adjustments=[ProviderReceiptAdjustment("discount", -50, "Rabatt", 0)],
    )


def test_fake_provider_contract_lists_and_fetches_receipts():
    fake = FakeLoyaltyProvider(
        provider_id="lidl_plus",
        capabilities=ProviderCapabilities(receipts=True, receipt_items=True),
        receipts=[_receipt()],
    )
    connection = ProviderConnection(1, 1, "lidl_plus", "lidl-1")
    page = asyncio.run(fake.list_receipts(connection, None, 10))
    receipt = asyncio.run(fake.get_receipt(connection, page.items[0]))
    assert page.items == ["ticket-1"]
    assert receipt.items[0].gtin == "4001234567899"
