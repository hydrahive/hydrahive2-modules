"""Begrenzter Parser für Lidls aktuelles htmlPrintedReceipt-Artikelformat."""
from __future__ import annotations

import re
from html.parser import HTMLParser

_MAX_HTML_CHARS = 2_000_000
_MAX_TAGS = 10_000
_MAX_ITEMS = 1000
_MAX_DISCOUNTS = 2000
_MAX_CAPTURE_TEXT = 4000
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_MONEY = re.compile(r"[-−]?\s*(?:EUR|€)?\s*\d[\d .]*(?:[,.]\d{1,2})?")
_DIRECT_MONEY = re.compile(r"\d[\d .]*[,.]\d{2}")
_BODY = re.compile(
    r"(?P<qty>[+-]?\d[\d.,]*)\s*\*\s*"
    r"(?P<unit>[+-]?\d[\d.,]*)\s+(?P<total>[+-]?\d[\d.,]*)"
)


class _ReceiptParser(HTMLParser):
    def __init__(self, warnings: list[str]):
        super().__init__(convert_charrefs=True)
        self.warnings = warnings
        self.items: list[dict] = []
        self.current: dict | None = None
        self.pending_article: dict | None = None
        self.article_depth = 0
        self.article_text: list[str] = []
        self.article_text_size = 0
        self.discount_depth = 0
        self.discount_text: list[str] = []
        self.discount_text_size = 0
        self.pending_discount: str | None = None
        self.discount_count = 0
        self.tag_count = 0
        self.budget_exhausted = False
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_count += 1
        if self.tag_count > _MAX_TAGS:
            self.budget_exhausted = True
            self._warn("html_tag_limit")
            return
        normalized_tag = tag.lower()
        if self.article_depth:
            self.article_depth += normalized_tag not in _VOID_TAGS
            return
        if self.discount_depth:
            self.discount_depth += normalized_tag not in _VOID_TAGS
            return
        if normalized_tag != "span":
            return
        data = {key.lower(): value or "" for key, value in attrs}
        classes = set(data.get("class", "").split())
        if "article" in classes:
            self.pending_discount = None
            self.article_depth = 1
            self.article_text, self.article_text_size = [], 0
            self.current = {
                "name": data.get("data-art-description"),
                "codeInput": data.get("data-art-id"),
                "quantity": data.get("data-art-quantity") or None,
                "currentUnitPrice": data.get("data-unit-price"),
                "taxGroupName": data.get("data-tax-type"),
                "discounts": [],
                "_html_source": True,
            }
        elif "discount" in classes and self.current is not None:
            self.discount_depth = 1
            self.discount_text, self.discount_text_size = [], 0
    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS:
            self.handle_endtag(tag)
    def handle_data(self, data: str) -> None:
        if self.budget_exhausted:
            return
        if self.article_depth:
            self.article_text_size = self._capture(
                self.article_text, self.article_text_size, data, "html_article_text_limit"
            )
        elif self.discount_depth:
            self.discount_text_size = self._capture(
                self.discount_text, self.discount_text_size, data, "html_discount_text_limit"
            )
    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _VOID_TAGS:
            return
        if self.article_depth:
            self.article_depth -= 1
            if not self.article_depth and tag.lower() == "span":
                self._finish_article()
            return
        if not self.discount_depth:
            return
        self.discount_depth -= 1
        if not self.discount_depth and tag.lower() == "span":
            self._finish_discount()
    def finish(self) -> None:
        self._flush_pending()
    def _finish_article(self) -> None:
        raw, self.current = self.current, None
        if raw is None:
            return
        text = " ".join("".join(self.article_text).split())
        body = _BODY.search(text)
        if body:
            if self.pending_article is not None and self._same_article(self.pending_article, raw):
                raw["discounts"] = self.pending_article["discounts"] + raw["discounts"]
                self.pending_article = None
            else:
                self._flush_pending()
            raw.update({
                "quantity": body["qty"], "currentUnitPrice": body["unit"],
                "originalAmount": body["total"],
            })
            self._append(raw)
        elif raw.get("quantity") is not None:
            self._flush_pending()
            self._append(raw)
        else:
            self._flush_pending()
            raw["quantity"] = "1"
            self.pending_article = raw
        self.current = raw
    def _finish_discount(self) -> None:
        text = " ".join("".join(self.discount_text).split())
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
            self._warn("html_discount_limit")
            return
        description = self.pending_discount or text[:match.start()].strip() or None
        amount = match.group().replace("−", "-").replace("EUR", "").replace("€", "").strip()
        self.current["discounts"].append({"description": description, "amount": amount})
        self.pending_discount = None
        self.discount_count += 1
    def _append(self, raw: dict) -> None:
        if len(self.items) >= _MAX_ITEMS:
            self._warn("html_item_limit")
            return
        self.items.append(raw)
    def _flush_pending(self) -> None:
        if self.pending_article is not None:
            self._append(self.pending_article)
            self.pending_article = None
    def _capture(self, parts: list[str], size: int, data: str, warning: str) -> int:
        remaining = _MAX_CAPTURE_TEXT - size
        if remaining <= 0:
            self._warn(warning)
            return size
        parts.append(data[:remaining])
        if len(data) > remaining:
            self._warn(warning)
        return size + min(len(data), remaining)

    @staticmethod
    def _same_article(first: dict, second: dict) -> bool:
        first_code, second_code = first.get("codeInput"), second.get("codeInput")
        if first_code or second_code:
            return bool(first_code and first_code == second_code)
        return first.get("name") == second.get("name")
    def _warn(self, warning: str) -> None:
        if warning not in self.warnings:
            self.warnings.append(warning)


def parse_html_items(value: object, warnings: list[str]) -> list[dict]:
    if not isinstance(value, str) or not value.strip():
        return []
    if len(value) > _MAX_HTML_CHARS:
        warnings.append("receipt_html_too_large")
        return []
    parser = _ReceiptParser(warnings)
    try:
        parser.feed(value)
        parser.close()
        parser.finish()
    except (ValueError, AssertionError):
        warnings.append("invalid_receipt_html")
        return []
    if not parser.items:
        warnings.append("html_items_missing")
    return parser.items
