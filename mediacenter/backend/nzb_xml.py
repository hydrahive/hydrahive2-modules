from __future__ import annotations

from .errors import IndexerResponseError
from .newznab_xml import parse_xml
from .redaction import text_contains_secret


def validate_nzb(data: bytes, secret: str) -> None:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise IndexerResponseError("indexer_xml_unsafe") from None
    if text_contains_secret(text, secret):
        raise IndexerResponseError("indexer_nzb_secret_reflected")
    root = parse_xml(data)
    if root.tag.rsplit("}", 1)[-1] != "nzb":
        raise IndexerResponseError("indexer_nzb_invalid")
    files = [node for node in root if node.tag.rsplit("}", 1)[-1] == "file"]
    if not files:
        raise IndexerResponseError("indexer_nzb_invalid")
    values = []
    for node in root.iter():
        values.extend(node.attrib.values())
        values.extend(value for value in (node.text, node.tail) if value)
    if any(text_contains_secret(value, secret) for value in values):
        raise IndexerResponseError("indexer_nzb_secret_reflected")
