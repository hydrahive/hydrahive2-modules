from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

from .config import MAX_TITLE_LENGTH
from .download_urls import safe_download_url
from .errors import IndexerAuthError, IndexerResponseError
from .models import IndexerCapabilities, RawRelease

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
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise IndexerResponseError("indexer_xml_unsafe") from None
    lowered = text.lower()
    if "\x00" in text or "<!doctype" in lowered or "<!entity" in lowered:
        raise IndexerResponseError("indexer_xml_unsafe")
    try:
        root = ET.fromstring(text)
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
    supported_params: dict[str, set[str]] = {}
    categories: set[int] = set()
    for node in root.iter():
        name = _local_name(node.tag)
        mapped = _SEARCH_NAMES.get(name)
        if mapped and (node.attrib.get("available") or "").lower() == "yes":
            search_types.add(mapped)
            supported_params[mapped] = {
                value.strip().lower()
                for value in node.attrib.get("supportedParams", "").split(",")
                if value.strip()
            }
        if name in {"category", "subcat"}:
            try:
                category = int(node.attrib.get("id", ""))
            except ValueError:
                continue
            if 0 < category <= 99_999:
                categories.add(category)

    if "search" not in search_types or not categories:
        raise IndexerResponseError("indexer_caps_invalid")
    return IndexerCapabilities(
        max_limit, default_limit, search_types, categories, supported_params
    )


def _text(item: ET.Element, name: str) -> str:
    for child in item:
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _attributes(item: ET.Element) -> dict[str, str] | None:
    result: dict[str, str] = {}
    for child in item:
        if _local_name(child.tag) != "attr":
            continue
        name = (child.attrib.get("name") or "").strip().lower()
        value = (child.attrib.get("value") or "").strip()
        if not name or name in result or len(name) > 64 or len(value) > 512:
            return None
        result[name] = value
    return result


def _positive_int(value: str | None) -> int | None:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return None
    return parsed if 0 <= parsed <= 10**15 else None


def _published(value: str):
    if not value or len(value) > 128:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _release(item: ET.Element) -> RawRelease | None:
    attrs = _attributes(item)
    if attrs is None:
        return None
    title = _text(item, "title")
    guid = attrs.get("guid") or _text(item, "guid")
    if not title or len(title) > MAX_TITLE_LENGTH or not guid or len(guid) > 512:
        return None

    enclosure = next(
        (child for child in item if _local_name(child.tag) == "enclosure"), None
    )
    raw_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
    if not raw_url:
        raw_url = _text(item, "link")
    size = _positive_int(attrs.get("size"))
    if size is None and enclosure is not None:
        size = _positive_int(enclosure.attrib.get("length"))
    category = _positive_int(attrs.get("category")) or 0

    return RawRelease(
        title=title,
        guid=guid,
        category_id=category,
        size_bytes=size,
        language=(attrs.get("language") or "").lower() or None,
        published_at=_published(_text(item, "pubDate")),
        download_url=safe_download_url(raw_url),
    )


def parse_search(data: bytes, *, max_items: int = 100) -> list[RawRelease]:
    root = parse_xml(data)
    if _local_name(root.tag) != "rss":
        raise IndexerResponseError("indexer_search_invalid")
    channel = next((node for node in root if _local_name(node.tag) == "channel"), None)
    if channel is None:
        raise IndexerResponseError("indexer_search_invalid")

    releases: list[RawRelease] = []
    for item in channel:
        if _local_name(item.tag) != "item":
            continue
        release = _release(item)
        if release is not None:
            releases.append(release)
        if len(releases) >= max(0, min(max_items, 100)):
            break
    return releases
