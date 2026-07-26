from __future__ import annotations

import io
import xml.etree.ElementTree as ET

from .errors import IndexerResponseError

MAX_XML_ELEMENTS = 100_000
MAX_XML_DEPTH = 64
MAX_XML_ATTRIBUTES = 200_000
MAX_ATTRIBUTES_PER_ELEMENT = 64


def validate_xml_structure(text: str) -> None:
    """Begrenzt XML-Struktur vor dem vollständigen ElementTree-Aufbau."""
    elements = 0
    attributes = 0
    depth = 0
    try:
        for event, element in ET.iterparse(
            io.StringIO(text), events=("start", "end")
        ):
            if event == "start":
                depth += 1
                elements += 1
                own_attributes = len(element.attrib)
                attributes += own_attributes
                if (
                    depth > MAX_XML_DEPTH
                    or elements > MAX_XML_ELEMENTS
                    or own_attributes > MAX_ATTRIBUTES_PER_ELEMENT
                    or attributes > MAX_XML_ATTRIBUTES
                ):
                    raise IndexerResponseError("indexer_xml_too_complex")
            else:
                depth -= 1
                element.clear()
    except IndexerResponseError:
        raise
    except (ET.ParseError, ValueError, OverflowError):
        raise IndexerResponseError("indexer_xml_invalid") from None
