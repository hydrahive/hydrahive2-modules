from __future__ import annotations

from backend.lidl_normalize import normalize_receipt


def test_normalizes_german_receipt_without_float_rounding():
    payload = {
        "id": "ticket-42",
        "date": "2026-07-18T14:30:00+02:00",
        "totalAmount": "4,98",
        "totalDiscount": "0,50",
        "currency": {"code": "EUR"},
        "store": {
            "id": "4711",
            "name": "Lidl Berlin",
            "address": "Teststraße 1, 10115 Berlin",
        },
        "itemsLine": [
            {
                "name": "Bio Milch",
                "quantity": "2,000",
                "isWeight": False,
                "currentUnitPrice": "2,49",
                "originalAmount": "4,98",
                "taxGroupName": "A",
                "codeInput": "4001234567899",
                "discounts": [{"description": "App Rabatt", "amount": "0,50"}],
                "deposit": {"amount": "0,25", "description": "Pfand"},
            }
        ],
    }
    receipt = normalize_receipt(payload)
    assert (receipt.total_minor, receipt.total_discount_minor, receipt.currency) == (498, 50, "EUR")
    assert (receipt.items[0].quantity, receipt.items[0].unit) == ("2.000", "piece")
    assert receipt.items[0].unit_price_minor == receipt.items[0].total_minor == 249 or receipt.items[0].total_minor == 498
    assert [(item.kind, item.amount_minor) for item in receipt.adjustments] == [
        ("discount", -50), ("deposit", 25)
    ]


def test_missing_and_inconsistent_fields_need_review_without_defaults():
    receipt = normalize_receipt({"id": "x", "itemsLine": [{"name": "Lose Ware", "codeInput": "invalid"}]})
    assert receipt.validation_status == "needs_review"
    assert receipt.total_minor is None
    assert receipt.currency is None
    assert receipt.items[0].gtin is None
    assert {"missing_total", "missing_currency", "invalid_gtin"} <= set(receipt.warnings)


def test_extreme_decimal_values_become_review_warnings_not_exceptions():
    receipt = normalize_receipt({
        "id": "huge", "date": "2026-07-18", "totalAmount": "1e999999",
        "currency": {"code": "EUR"}, "itemsLine": [],
    })
    assert receipt.total_minor is None
    assert receipt.validation_status == "needs_review"
    assert "missing_total" in receipt.warnings


def test_normalized_model_and_hash_do_not_retain_raw_payload():
    secret = "must-not-persist"
    receipt = normalize_receipt({
        "id": "safe", "date": "2026-07-18", "totalAmount": "1,00",
        "currency": {"code": "EUR"}, "itemsLine": [], "unknown": secret,
    })
    assert secret not in repr(receipt)
    assert not hasattr(receipt, "raw_payload")
