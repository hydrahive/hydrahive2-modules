"""Begrenzt sammeln und gruppieren von Lidl-HTML-Zeilenfragmenten."""
from __future__ import annotations

from html.parser import HTMLParser

_MAX_HTML_CHARS = 2_000_000
_MAX_TAGS = 10_000
_MAX_LINES = 3000
_MAX_CAPTURE_TEXT = 4000
_VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta source track wbr".split()
)
_IDENTITY_FIELDS = (
    "data-art-id", "data-art-description", "data-art-quantity", "data-unit-price",
)


class _LineCollector(HTMLParser):
    def __init__(self, warnings: list[str]):
        super().__init__(convert_charrefs=True)
        self.warnings = warnings
        self.lines: dict[str, dict] = {}
        self.variants: dict[str, list[str]] = {}
        self.order: list[str] = []
        self.active: str | None = None
        self.depth = 0
        self.fallback = 0
        self.tag_count = 0
        self.exhausted = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_count += 1
        if self.tag_count > _MAX_TAGS:
            self.exhausted = True
            self._warn("html_tag_limit")
            return
        normalized_tag = tag.lower()
        if self.active is not None:
            self.depth += normalized_tag not in _VOID_TAGS
            return
        if normalized_tag != "span":
            return
        data = {key.lower(): value or "" for key, value in attrs}
        classes = set(data.get("class", "").split())
        kind = "article" if "article" in classes else (
            "discount" if "discount" in classes else None
        )
        if kind is None:
            return
        line_id = data.get("id")
        base = f"{kind}:{line_id}" if line_id else ""
        candidates = self.variants.get(base, []) if base else []
        key = next(
            (candidate for candidate in candidates
             if self._compatible(self.lines[candidate]["attrs"], data)),
            "",
        )
        if not key:
            if len(self.lines) >= _MAX_LINES:
                self._warn("html_line_limit")
                return
            key = base if base and not candidates else f"{kind}:_fallback_{self.fallback}"
            self.fallback += 1
            self.lines[key] = {
                "kind": kind, "line_id": line_id or None, "attrs": data,
                "parts": [], "text_size": 0,
            }
            self.order.append(key)
            if base:
                self.variants.setdefault(base, []).append(key)
                if candidates:
                    self._warn("html_line_id_conflict")
        stored = self.lines[key]["attrs"]
        for name, value in data.items():
            if value and not stored.get(name):
                stored[name] = value
        self.active, self.depth = key, 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.active is None or self.exhausted:
            return
        line = self.lines[self.active]
        remaining = _MAX_CAPTURE_TEXT - line["text_size"]
        if remaining <= 0:
            self._warn("html_line_text_limit")
            return
        line["parts"].append(data[:remaining])
        line["text_size"] += min(len(data), remaining)
        if len(data) > remaining:
            self._warn("html_line_text_limit")

    def handle_endtag(self, tag: str) -> None:
        if self.active is None or tag.lower() in _VOID_TAGS:
            return
        self.depth -= 1
        if self.depth == 0:
            self.active = None

    def result(self) -> list[dict]:
        return [
            {**self.lines[key], "text": "".join(self.lines[key]["parts"])}
            for key in self.order
        ]

    @staticmethod
    def _compatible(stored: dict, incoming: dict) -> bool:
        return all(
            not stored.get(field) or not incoming.get(field)
            or stored[field] == incoming[field]
            for field in _IDENTITY_FIELDS
        )

    def _warn(self, warning: str) -> None:
        if warning not in self.warnings:
            self.warnings.append(warning)


def collect_html_lines(value: object, warnings: list[str]) -> list[dict]:
    if not isinstance(value, str) or not value.strip():
        return []
    if len(value) > _MAX_HTML_CHARS:
        warnings.append("receipt_html_too_large")
        return []
    collector = _LineCollector(warnings)
    try:
        collector.feed(value)
        collector.close()
    except (ValueError, AssertionError):
        warnings.append("invalid_receipt_html")
        return []
    return collector.result()
