"""Normalisierung gruppierter Lidl-htmlPrintedReceipt-Zeilen."""
from __future__ import annotations

import re

from .lidl_html_lines import collect_html_lines

_MAX_ITEMS = 1000
_MAX_DISCOUNTS = 2000
_MONEY = re.compile(r"[-−]?\s*(?:EUR|€)?\s*\d[\d .]*(?:[,.]\d{1,2})?")
_DIRECT_MONEY = re.compile(r"\d[\d .]*[,.]\d{2}")
_LEGACY_LINE_A = re.compile(r"^line_\d+a$")
_BODY = re.compile(
    r"\s*(?P<qty>[+-]?\d[\d.,]*)\s*\*\s*"
    r"(?P<unit>[+-]?\d[\d.,]*)\s+(?P<total>[+-]?\d[\d.,]*)"
    r"(?:\s+[A-Za-z])?\s*"
)


class _LineNormalizer:
    def __init__(self, warnings: list[str]):
        self.warnings = warnings
        self.items: list[dict] = []
        self.current: dict | None = None
        self.pending_article: dict | None = None
        self.pending_discount: str | None = None
        self.discount_count = 0

    def consume(self, lines: list[dict]) -> list[dict]:
        for line in lines:
            text = " ".join(line["text"].split())
            if line["kind"] == "article":
                self._article(line["attrs"], text, line.get("line_id"))
            else:
                self._discount(text)
        self._flush_pending()
        return self.items

    def _article(self, attrs: dict, text: str, line_id: str | None) -> None:
        self.pending_discount = None
        raw = {
            "name": attrs.get("data-art-description"),
            "codeInput": attrs.get("data-art-id"),
            "quantity": attrs.get("data-art-quantity") or None,
            "currentUnitPrice": attrs.get("data-unit-price"),
            "taxGroupName": attrs.get("data-tax-type"),
            "discounts": [], "_html_source": True, "_line_id": line_id,
        }
        paired_line = self.pending_article is not None and self._paired_ids(
            self.pending_article.get("_line_id"), line_id,
        )
        body = _BODY.fullmatch(text) if line_id is None or paired_line else None
        if body:
            if self.pending_article is not None and self._same(self.pending_article, raw):
                previous = self.pending_article
                for field in ("name", "codeInput", "currentUnitPrice", "taxGroupName"):
                    raw[field] = raw.get(field) or previous.get(field)
                raw["discounts"] = previous["discounts"]
                self.pending_article = None
            else:
                if paired_line and self.pending_article is not None:
                    self.warnings.append("html_legacy_pair_conflict")
                self._flush_pending()
            raw["quantity"] = body["qty"]
            raw["currentUnitPrice"] = raw["currentUnitPrice"] or body["unit"]
            raw["originalAmount"] = body["total"]
            self._append(raw)
        elif raw["quantity"] is not None:
            self._flush_pending()
            self._append(raw)
        else:
            self._flush_pending()
            raw["quantity"] = "1"
            self.pending_article = raw
        self.current = raw

    def _discount(self, text: str) -> None:
        if not text or self.current is None:
            return
        match = None
        for candidate in _MONEY.finditer(text):
            match = candidate
        is_money = match is not None and not text[match.end():].strip()
        has_signal = bool(match and (
            "-" in match.group() or "−" in match.group() or "€" in match.group()
            or "EUR" in match.group().upper() or self.pending_discount
            or _DIRECT_MONEY.fullmatch(text)
        ))
        if not is_money or not has_signal:
            self.pending_discount = text[:1000]
            return
        if self.discount_count >= _MAX_DISCOUNTS:
            if "html_discount_limit" not in self.warnings:
                self.warnings.append("html_discount_limit")
            return
        description = self.pending_discount or text[:match.start()].strip() or None
        amount = (
            match.group().replace("−", "-").replace("EUR", "").replace("€", "").strip()
        )
        self.current["discounts"].append({"description": description, "amount": amount})
        self.pending_discount = None
        self.discount_count += 1

    def _append(self, raw: dict) -> None:
        if len(self.items) >= _MAX_ITEMS:
            if "html_item_limit" not in self.warnings:
                self.warnings.append("html_item_limit")
            return
        self.items.append(raw)

    def _flush_pending(self) -> None:
        if self.pending_article is not None:
            self._append(self.pending_article)
            self.pending_article = None

    @staticmethod
    def _paired_ids(first: str | None, second: str | None) -> bool:
        return bool(
            first and second and _LEGACY_LINE_A.fullmatch(first)
            and second == first[:-1] + "b"
        )

    @staticmethod
    def _identity_compatible(first: dict, second: dict) -> bool:
        return all(
            not first.get(field) or not second.get(field) or first[field] == second[field]
            for field in ("codeInput", "name", "currentUnitPrice")
        )

    @classmethod
    def _same(cls, first: dict, second: dict) -> bool:
        first_line, second_line = first.get("_line_id"), second.get("_line_id")
        if first_line is not None or second_line is not None:
            return cls._paired_ids(first_line, second_line) and cls._identity_compatible(
                first, second,
            )
        first_code, second_code = first.get("codeInput"), second.get("codeInput")
        if first_code or second_code:
            return bool(first_code and first_code == second_code)
        return first.get("name") == second.get("name")


def parse_html_items(value: object, warnings: list[str]) -> list[dict]:
    lines = collect_html_lines(value, warnings)
    try:
        items = _LineNormalizer(warnings).consume(lines)
    except (ValueError, AssertionError):
        warnings.append("invalid_receipt_html")
        return []
    if not items and isinstance(value, str) and value.strip():
        warnings.append("html_items_missing")
    return items
