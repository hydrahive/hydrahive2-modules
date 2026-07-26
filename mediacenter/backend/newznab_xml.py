from __future__ import annotations

import xml.etree.ElementTree as ET

from .errors import IndexerAuthError, IndexerResponseError
from .models import IndexerCapabilities

_SEARCH_NAMES = {
    "search": "search",
    "movie-search": "movie",
    "tv-search": "tv",
    "music-search": "music",
    "book-search": "book",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_xml(data: bytes) -> ET.Element:
    """Parst kleines, UTF-8-basiertes Newznab-XML ohne DTD/Entities."""
    lowered = data.lower()
    if b"\x00" in data or b"<!doctype" in lowered or b"<!entity" in lowered:
        raise IndexerResponseError("indexer_xml_unsafe")
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError, OverflowError) as exc:
        raise IndexerResponseError("indexer_xml_invalid") from exc
    if _local_name(root.tag) == "error":
        code = (root.attrib.get("code") or "").strip()
        if code in {"100", "101", "102"}:
            raise IndexerAuthError("indexer_auth_failed")
        raise IndexerResponseError("indexer_api_error")
    return root


def _bounded_int(value: str | None, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def parse_caps(data: bytes) -> IndexerCapabilities:
    root = parse_xml(data)
    if _local_name(root.tag) != "caps":
        raise IndexerResponseError("indexer_caps_invalid")

    limits = next((node for node in root if _local_name(node.tag) == "limits"), None)
    max_limit = _bounded_int(
        limits.attrib.get("max") if limits is not None else None,
        100,
        minimum=1,
        maximum=500,
    )
    default_limit = _bounded_int(
        limits.attrib.get("default") if limits is not None else None,
        min(100, max_limit),
        minimum=1,
        maximum=max_limit,
    )

    search_types: set[str] = set()
    categories: set[int] = set()
    for node in root.iter():
        name = _local_name(node.tag)
        mapped = _SEARCH_NAMES.get(name)
        if mapped and (node.attrib.get("available") or "").lower() == "yes":
            search_types.add(mapped)
        if name in {"category", "subcat"}:
            try:
                category = int(node.attrib.get("id", ""))
            except ValueError:
                continue
            if 0 < category <= 99_999:
                categories.add(category)

    if "search" not in search_types or not categories:
        raise IndexerResponseError("indexer_caps_invalid")
    return IndexerCapabilities(max_limit, default_limit, search_types, categories)
