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


def test_normalizes_current_html_receipt_with_nested_money_and_de_timezone():
    payload = {
        "id": "html-ticket",
        "date": "2026-07-18T13:35:33",
        "totalAmount": {"amount": "2,04", "currency": {"code": "EUR"}},
        "store": {
            "id": "DE-1",
            "name": "Lidl Teststadt",
            "address": "Teststraße 16",
        },
        "htmlPrintedReceipt": """
            <span class="article" data-art-id="4001234567899"
                data-art-description="Cr&egrave;me &amp; Brot"
                data-unit-price="1,29" data-tax-type="A">Artikel</span>
            <span class="article" data-art-id="0000000067890"
                data-art-description="Lose Bananen" data-art-quantity="0,5"
                data-unit-price="2,00" data-tax-type="A">Artikel</span>
            <span class="discount">Obst Coupon</span>
            <span class="discount">-0,25</span>
        """,
        "couponsUsed": [
            {
                "title": "App Coupon", "discount": "Aktionscoupon",
                "couponTitle": "0,10 €",
            }
        ],
    }
    receipt = normalize_receipt(payload)
    assert (receipt.total_minor, receipt.currency, receipt.total_discount_minor) == (
        204, "EUR", 35,
    )
    assert [item.original_name for item in receipt.items] == [
        "Crème & Brot", "Lose Bananen",
    ]
    assert [(item.quantity, item.unit, item.total_minor) for item in receipt.items] == [
        ("1", "piece", 129), ("0.5", "kg", 100),
    ]
    assert [(item.kind, item.amount_minor, item.item_sequence) for item in receipt.adjustments] == [
        ("discount", -25, 1), ("coupon", -10, -1),
    ]
    assert [item.description for item in receipt.adjustments] == [
        "Obst Coupon", "App Coupon",
    ]
    assert receipt.purchased_at is not None
    assert receipt.purchased_at.utcoffset() is not None
    assert {"timezone_inferred_de", "total_discount_derived"} <= set(receipt.warnings)
    assert not {
        "missing_total", "missing_currency", "timezone_unknown", "coupon_amount_unknown",
    } & set(receipt.warnings)
    assert "htmlPrintedReceipt" not in repr(receipt)


def test_real_de_css_fragments_group_by_html_line_id_without_losing_repeats():
    def spans(line_id: str, attrs: str, parts: list[str], count: int) -> str:
        values = parts + [""] * (count - len(parts))
        return "".join(
            f'<span id="{line_id}" class="article" {attrs}>{value}</span>'
            for value in values
        )

    basic = 'data-art-id="111" data-art-description="Brot" data-unit-price="1,00" data-tax-type="A"'
    quantity = (
        'data-art-id="222" data-art-description="Milch" data-art-quantity="2" '
        'data-unit-price="1,50" data-tax-type="A"'
    )
    discount_parts = ["App ", "Coupon", "", "", "-0,50"]
    discounts = "".join(
        f'<span id="discount_1" class="discount">{part}</span>'
        for part in discount_parts
    )
    receipt = normalize_receipt({
        "id": "de-fragments", "date": "2026-07-18T10:00:00",
        "totalAmount": "4,50",
        "htmlPrintedReceipt": (
            spans("purchase_list_line_1", basic, ["Brot"], 6)
            + spans("purchase_list_line_2", quantity, ["Milch", "2", " x ", "1,50"], 13)
            + discounts
            + spans("purchase_list_line_3", basic, ["Brot"], 6)
        ),
        "couponsUsed": [{"title": "App Coupon", "discount": "0,50 €"}],
    })
    assert [(item.original_name, item.quantity, item.total_minor) for item in receipt.items] == [
        ("Brot", "1", 100), ("Milch", "2", 300), ("Brot", "1", 100),
    ]
    assert [(item.description, item.amount_minor) for item in receipt.adjustments] == [
        ("App Coupon", -50),
    ]
    assert receipt.total_discount_minor == 50
    assert receipt.validation_status == "valid"
    assert not {"coupon_amount_unknown", "missing_total"} & set(receipt.warnings)


def test_conflicting_fragments_with_same_html_id_are_split_and_flagged():
    first = (
        '<span id="same" class="article" data-art-id="111" '
        'data-art-description="Brot" data-unit-price="1,00">Brot</span>'
    )
    second = (
        '<span id="same" class="article" data-art-id="222" '
        'data-art-description="Milch" data-unit-price="2,00">Milch</span>'
    )
    receipt = normalize_receipt({
        "id": "id-conflict", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "3,00", "currency": "EUR",
        "htmlPrintedReceipt": first + second,
    })
    assert [item.original_name for item in receipt.items] == ["Brot", "Milch"]
    assert "html_line_id_conflict" in receipt.warnings
    assert receipt.validation_status == "needs_review"


def test_html_ids_prevent_adjacent_equal_products_from_being_merged():
    receipt = normalize_receipt({
        "id": "adjacent-equal", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "3,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span id="row_1" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">Brot</span>'
            '<span id="row_2" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">2 * 1,00 2,00</span>'
        ),
    })
    assert len(receipt.items) == 2


def test_pack_size_in_named_html_line_is_not_interpreted_as_quantity():
    receipt = normalize_receipt({
        "id": "pack-size", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "3,99", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span id="row_1" class="article" data-art-id="333" '
            'data-art-description="Batterien 2x4" data-unit-price="3,99">'
            "Batterien 2x4</span>"
        ),
    })
    assert (receipt.items[0].quantity, receipt.items[0].total_minor) == ("1", 399)


def test_current_two_span_article_rows_collapse_to_one_exact_line_item():
    attrs = (
        'class="article" data-art-id="5530547" '
        'data-art-description="Bio Butter" data-unit-price="4,99"'
    )
    receipt = normalize_receipt({
        "id": "two-span", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "14,97", "currency": "EUR",
        "htmlPrintedReceipt": (
            f'<span id="line_1a" {attrs}>Bio Butter</span>'
            f'<span id="line_1b" {attrs}>3 * 4.99 14.97 C</span>'
        ),
    })
    assert len(receipt.items) == 1
    item = receipt.items[0]
    assert (item.original_name, item.quantity, item.unit_price_minor, item.total_minor) == (
        "Bio Butter", "3", 499, 1497,
    )


def test_legacy_pair_requires_exact_id_schema_and_matching_identity():
    conflicting = normalize_receipt({
        "id": "legacy-conflict", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "3,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span id="line_1a" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">Brot</span>'
            '<span id="line_1b" class="article" data-art-id="222" '
            'data-art-description="Milch" data-unit-price="1,00">2 * 1,00 2,00</span>'
        ),
    })
    sparse_body = normalize_receipt({
        "id": "sparse-body", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "2,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span id="line_2a" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">Brot</span>'
            '<span id="line_2b" class="article">2 * 1,00 2,00</span>'
        ),
    })
    suffixed_body = normalize_receipt({
        "id": "suffixed-body", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "3,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span id="line_3a" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">Brot</span>'
            '<span id="line_3b" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">'
            "2 * 1,00 2,00 Zusatz</span>"
        ),
    })
    unrelated = normalize_receipt({
        "id": "unrelated-ab", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "3,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span id="fooa" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">Brot</span>'
            '<span id="foob" class="article" data-art-id="111" '
            'data-art-description="Brot" data-unit-price="1,00">2 * 1,00 2,00</span>'
        ),
    })
    assert len(conflicting.items) == 2
    assert "html_legacy_pair_conflict" in conflicting.warnings
    assert conflicting.validation_status == "needs_review"
    assert [(item.original_name, item.quantity, item.total_minor) for item in sparse_body.items] == [
        ("Brot", "2", 200),
    ]
    assert len(suffixed_body.items) == 2
    assert len(unrelated.items) == 2


def test_numeric_coupon_name_is_not_misread_as_a_discount_amount():
    receipt = normalize_receipt({
        "id": "numeric-coupon", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "0,50", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span class="article" data-art-description="Artikel" '
            'data-art-quantity="1" data-unit-price="1,00"></span>'
            '<span class="discount">Coupon 5</span>'
            '<span class="discount">-0,50</span>'
        ),
    })
    assert [(item.description, item.amount_minor) for item in receipt.adjustments] == [
        ("Coupon 5", -50),
    ]


def test_coupon_already_present_in_html_is_not_counted_twice():
    receipt = normalize_receipt({
        "id": "duplicate-coupon", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "0,50", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span class="article" data-art-description="Artikel" '
            'data-art-quantity="1" data-unit-price="1,00"></span>'
            '<span class="discount">App Coupon</span>'
            '<span class="discount">-0,50</span>'
        ),
        "couponsUsed": [{"title": "App Coupon", "couponTitle": "0,50 €"}],
    })
    assert len(receipt.adjustments) == 1
    assert receipt.total_discount_minor == 50


def test_repeated_equal_coupons_preserve_multiplicity():
    receipt = normalize_receipt({
        "id": "repeated-coupons", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR", "itemsLine": [],
        "couponsUsed": [
            {"title": "App Coupon", "couponTitle": "0,50 €"},
            {"title": "App Coupon", "couponTitle": "0,50 €"},
        ],
    })
    assert len(receipt.adjustments) == 2
    assert receipt.total_discount_minor == 100


def test_coupon_metadata_without_amount_is_always_informational():
    covered = normalize_receipt({
        "id": "coupon-metadata-covered", "date": "2026-07-18T10:00:00",
        "totalAmount": "0,50",
        "itemsLine": [{
            "name": "Artikel",
            "discounts": [{"description": "App Coupon", "amount": "0,50"}],
        }],
        "couponsUsed": [{
            "title": "Andere Anzeige", "couponDescription": "App Coupon",
            "discount": "Aktionscoupon",
        }],
    })
    uncovered = normalize_receipt({
        "id": "coupon-metadata-uncovered", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR", "itemsLine": [],
        "couponsUsed": [{"title": "App Coupon", "discount": "Aktionscoupon"}],
    })
    ambiguous = normalize_receipt({
        "id": "coupon-metadata-ambiguous", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{
            "name": "Artikel", "discounts": [
                {"description": "App Coupon", "amount": "0,25"},
                {"description": "App Coupon", "amount": "0,25"},
            ],
        }],
        "couponsUsed": [{"title": "App Coupon", "discount": "Aktionscoupon"}],
    })
    unnamed = normalize_receipt({
        "id": "coupon-metadata-unnamed", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{"name": "Artikel", "discounts": [{"amount": "0,25"}]}],
        "couponsUsed": [{"title": " ", "discount": "Aktionscoupon"}],
    })
    for receipt in (covered, uncovered, ambiguous, unnamed):
        assert receipt.validation_status == "valid"
        assert "coupon_metadata_without_amount" in receipt.warnings
        assert "coupon_amount_unknown" not in receipt.warnings


def test_non_object_coupon_stays_a_reviewable_provider_error():
    receipt = normalize_receipt({
        "id": "invalid-coupon", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR", "itemsLine": [],
        "couponsUsed": [None, "0,50", 5],
    })
    assert receipt.validation_status == "needs_review"
    assert "invalid_coupon" in receipt.warnings
    assert receipt.adjustments == []


def test_invalid_explicit_coupon_amount_stays_reviewable():
    for value in ("defekt", True):
        receipt = normalize_receipt({
            "id": f"invalid-coupon-amount-{value}",
            "date": "2026-07-18T10:00:00+02:00", "totalAmount": "1,00",
            "currency": "EUR", "itemsLine": [],
            "couponsUsed": [{"title": "Coupon", "amount": value}],
        })
        assert receipt.validation_status == "needs_review"
        assert "invalid_coupon_amount" in receipt.warnings


def test_different_product_codes_with_same_name_are_not_collapsed():
    first = 'class="article" data-art-id="111" data-art-description="Brot" data-unit-price="1,00"'
    second = 'class="article" data-art-id="222" data-art-description="Brot" data-unit-price="1,00"'
    receipt = normalize_receipt({
        "id": "different-codes", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "2,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            f"<span {first}>Brot</span><span {second}>1 * 1.00 1.00 C</span>"
        ),
    })
    assert len(receipt.items) == 2


def test_one_missing_product_code_does_not_merge_two_span_rows():
    receipt = normalize_receipt({
        "id": "missing-second-code", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "2,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span class="article" data-art-id="111" data-art-description="Brot" '
            'data-unit-price="1,00">Brot</span>'
            '<span class="article" data-art-description="Brot" data-unit-price="1,00">'
            "1 * 1.00 1.00 C</span>"
        ),
    })
    assert len(receipt.items) == 2


def test_void_html_elements_do_not_swallow_article_rows():
    receipt = normalize_receipt({
        "id": "void-element", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "htmlPrintedReceipt": (
            '<span class="article" data-art-description="Brot" data-art-quantity="1" '
            'data-unit-price="1,00">Brot<br>1,00</span>'
        ),
    })
    assert [(item.original_name, item.total_minor) for item in receipt.items] == [
        ("Brot", 100),
    ]


def test_html_receipt_parser_caps_article_count():
    article = '<span class="article" data-art-description="Artikel" data-unit-price="1,00"></span>'
    receipt = normalize_receipt({
        "id": "large-html", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1001,00", "currency": "EUR",
        "htmlPrintedReceipt": article * 1001,
    })
    assert len(receipt.items) == 1000
    assert "html_item_limit" in receipt.warnings


def test_structured_item_count_is_capped():
    receipt = normalize_receipt({
        "id": "large-json", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1001,00", "currency": "EUR",
        "itemsLine": [{"name": "Artikel", "currentUnitPrice": "1,00"}] * 1001,
    })
    assert len(receipt.items) == 1000
    assert "item_limit" in receipt.warnings


def test_matching_html_coupon_does_not_consume_adjustment_capacity():
    discounts = [{"description": "Match", "amount": "0,01"}] * 1999
    receipt = normalize_receipt({
        "id": "coupon-capacity", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{"name": "Artikel", "discounts": discounts}],
        "couponsUsed": [
            {"title": "Match", "couponTitle": "0,01 €"},
            {"title": "New", "couponTitle": "0,02 €"},
        ],
    })
    assert len(receipt.adjustments) == 2000
    assert receipt.adjustments[-1].description == "New"


def test_dropped_deposit_at_adjustment_cap_is_marked_for_review():
    discounts = [{"description": "Rabatt", "amount": "0,01"}] * 2000
    receipt = normalize_receipt({
        "id": "deposit-cap", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{
            "name": "Artikel", "discounts": discounts, "deposit": "0,25",
        }],
    })
    assert len(receipt.adjustments) == 2000
    assert "adjustment_limit" in receipt.warnings


def test_internal_lidl_product_code_is_not_a_reviewable_gtin_error():
    receipt = normalize_receipt({
        "id": "internal-product-code", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{"name": "Artikel", "codeInput": "1234567"}],
    })
    assert receipt.items[0].gtin is None
    assert "invalid_gtin" in receipt.warnings
    assert receipt.validation_status == "valid"


def test_missing_and_inconsistent_fields_need_review_with_marked_de_currency():
    receipt = normalize_receipt({"id": "x", "itemsLine": [{"name": "Lose Ware", "codeInput": "invalid"}]})
    assert receipt.validation_status == "needs_review"
    assert receipt.total_minor is None
    assert receipt.currency == "EUR"
    assert receipt.items[0].gtin is None
    assert {"missing_total", "currency_inferred_de", "invalid_gtin"} <= set(receipt.warnings)


def test_old_item_format_defaults_missing_quantity_to_one():
    receipt = normalize_receipt({
        "id": "old-default-quantity", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "2,49", "currency": "EUR",
        "itemsLine": [{"name": "Brot", "currentUnitPrice": "2,49"}],
    })
    assert (receipt.items[0].quantity, receipt.items[0].total_minor) == ("1", 249)


def test_localized_grouping_formats_are_normalized_without_float_rounding():
    for index, value in enumerate(("1,234.56", "1.234,56")):
        receipt = normalize_receipt({
            "id": f"localized-{index}", "date": "2026-07-18T10:00:00+02:00",
            "totalAmount": value, "currency": "EUR", "itemsLine": [],
        })
        assert receipt.total_minor == 123456


def test_malformed_grouping_and_subcent_totals_are_rejected():
    for index, value in enumerate(("12,34.56", "1,23,4.56", "1,234")):
        receipt = normalize_receipt({
            "id": f"malformed-money-{index}", "date": "2026-07-18T10:00:00+02:00",
            "totalAmount": value, "currency": "EUR", "itemsLine": [],
        })
        assert receipt.total_minor is None
        assert "missing_total" in receipt.warnings


def test_extreme_item_quantity_is_rejected_without_fixed_point_expansion():
    receipt = normalize_receipt({
        "id": "huge-quantity", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{
            "name": "Artikel", "quantity": "1e999999", "currentUnitPrice": "1,00",
        }],
    })
    assert receipt.items[0].quantity is None
    assert "invalid_quantity" in receipt.warnings


def test_invalid_or_conflicting_currency_is_not_silently_inferred():
    invalid = normalize_receipt({
        "id": "invalid-currency", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EURO", "itemsLine": [],
    })
    conflict = normalize_receipt({
        "id": "currency-conflict", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": {"amount": "1,00", "currency": "USD"},
        "currency": "EUR", "itemsLine": [],
    })
    assert invalid.currency is None and "invalid_currency" in invalid.warnings
    assert conflict.currency is None and "invalid_currency" in conflict.warnings


def test_scalar_total_is_never_interpreted_as_currency_and_null_alias_falls_back():
    invalid_total = normalize_receipt({
        "id": "nan-total", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "NAN", "itemsLine": [],
    })
    non_eur_total = normalize_receipt({
        "id": "dollar-total", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "$1.00", "itemsLine": [],
    })
    fallback_total = normalize_receipt({
        "id": "fallback-total", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": None, "total": "2,00", "currency": "EUR", "itemsLine": [],
    })
    assert invalid_total.total_minor is None and invalid_total.currency == "EUR"
    assert non_eur_total.total_minor is None and "missing_total" in non_eur_total.warnings
    assert fallback_total.total_minor == 200


def test_discount_field_is_coupon_specific_and_invalid_total_discount_needs_review():
    wrong_total = normalize_receipt({
        "id": "wrong-total-shape", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": {"amount": None, "discount": "0,50"},
        "currency": "EUR", "itemsLine": [],
    })
    invalid_discount = normalize_receipt({
        "id": "invalid-discount", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR", "totalDiscount": "defekt",
        "itemsLine": [{
            "name": "Artikel", "discounts": [{"description": "Rabatt", "amount": "0,20"}],
        }],
    })
    assert wrong_total.total_minor is None and "missing_total" in wrong_total.warnings
    assert "invalid_total_discount" in invalid_discount.warnings
    assert invalid_discount.validation_status == "needs_review"


def test_punctuation_distinct_coupons_are_not_deduplicated():
    receipt = normalize_receipt({
        "id": "coupon-punctuation", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "itemsLine": [{
            "name": "Artikel", "discounts": [{"description": "A+B", "amount": "0,50"}],
        }],
        "couponsUsed": [{"title": "AB", "discount": "0,50 €"}],
    })
    assert [item.description for item in receipt.adjustments] == ["A+B", "AB"]


def test_dst_gap_and_overlap_remain_explicitly_unresolved():
    nonexistent = normalize_receipt({
        "id": "dst-gap", "date": "2026-03-29T02:30:00",
        "totalAmount": "1,00", "currency": "EUR", "itemsLine": [],
    })
    ambiguous = normalize_receipt({
        "id": "dst-overlap", "date": "2026-10-25T02:30:00",
        "totalAmount": "1,00", "currency": "EUR", "itemsLine": [],
    })
    assert nonexistent.purchased_at is not None and nonexistent.purchased_at.tzinfo is None
    assert ambiguous.purchased_at is not None and ambiguous.purchased_at.tzinfo is None
    assert "timezone_nonexistent" in nonexistent.warnings
    assert "timezone_ambiguous" in ambiguous.warnings


def test_derived_discount_sum_cannot_exceed_signed_sqlite_integer():
    maximum = "92233720368547758,07 €"
    receipt = normalize_receipt({
        "id": "discount-overflow", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR", "itemsLine": [],
        "couponsUsed": [
            {"title": "Coupon A", "couponTitle": maximum},
            {"title": "Coupon B", "couponTitle": maximum},
        ],
    })
    assert receipt.total_discount_minor is None
    assert "total_discount_out_of_range" in receipt.warnings


def test_oversized_receipt_html_is_not_parsed():
    receipt = normalize_receipt({
        "id": "oversized-html", "date": "2026-07-18T10:00:00+02:00",
        "totalAmount": "1,00", "currency": "EUR",
        "htmlPrintedReceipt": "x" * 2_000_001,
    })
    assert receipt.items == []
    assert "receipt_html_too_large" in receipt.warnings


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
