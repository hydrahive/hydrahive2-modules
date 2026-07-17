from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date
from decimal import Decimal, InvalidOperation

from .import_parsers import (
    ImportParseError,
    MAX_RECORDS,
    NormalizedRecord,
    mask_bank_identifier,
    normalize_bank_reference,
)

_FORBIDDEN_XML = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
_ALLOWED_NAMESPACES = {
    "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02",
    "urn:iso:std:iso:20022:tech:xsd:camt.053.001.08",
}


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local(child) == name]


def _desc(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element.iter() if _local(child) == name]


def _text(element: ET.Element, *names: str) -> str | None:
    current = element
    for name in names:
        found = next((child for child in current if _local(child) == name), None)
        if found is None:
            return None
        current = found
    value = " ".join("".join(current.itertext()).split())
    return value or None


def _first_desc_text(element: ET.Element, name: str) -> str | None:
    found = next(iter(_desc(element, name)), None)
    if found is None:
        return None
    value = " ".join("".join(found.itertext()).split())
    return value or None


def _path_node(element: ET.Element, *names: str) -> ET.Element | None:
    current = element
    for name in names:
        current = next((child for child in current if _local(child) == name), None)
        if current is None:
            return None
    return current


def _minor(value: str, sign: str | None) -> int:
    try:
        amount = Decimal(value)
        quantized = amount.quantize(Decimal("0.01"))
        if amount != quantized:
            raise ValueError
        minor = int(quantized * 100)
    except (InvalidOperation, ValueError) as exc:
        raise ImportParseError("invalid_amount") from exc
    return -abs(minor) if sign == "DBIT" else abs(minor)


def _party(details: ET.Element, sign: str) -> tuple[str | None, str | None]:
    party_name = "Cdtr" if sign == "DBIT" else "Dbtr"
    account_name = "CdtrAcct" if sign == "DBIT" else "DbtrAcct"
    party = next(iter(_desc(details, party_name)), None)
    account = next(iter(_desc(details, account_name)), None)
    return (
        _first_desc_text(party, "Nm") if party is not None else None,
        mask_bank_identifier(_first_desc_text(account, "IBAN"))
        if account is not None
        else None,
    )


def _detail_amount(
    detail: ET.Element, entry_amount: ET.Element | None, *, allow_entry: bool
) -> ET.Element | None:
    for path in (("AmtDtls", "TxAmt", "Amt"), ("AmtDtls", "InstdAmt", "Amt")):
        found = _path_node(detail, *path)
        if found is not None:
            return found
    return entry_amount if allow_entry else None


def _parse_detail(
    entry: ET.Element,
    detail: ET.Element,
    entry_amount: ET.Element | None,
    source_line: int,
    *,
    allow_entry_amount: bool,
) -> NormalizedRecord:
    amount_node = _detail_amount(detail, entry_amount, allow_entry=allow_entry_amount)
    booking = _text(entry, "BookgDt", "Dt") or _text(entry, "BookgDt", "DtTm")
    if amount_node is None or not amount_node.text:
        raise ImportParseError("camt_batch_amount_missing")
    if not booking:
        raise ImportParseError("invalid_camt_record")
    sign = _first_desc_text(detail, "CdtDbtInd") or _text(entry, "CdtDbtInd") or "CRDT"
    currency = (amount_node.attrib.get("Ccy") or "").upper()
    try:
        booking_date = date.fromisoformat(booking[:10])
        value_raw = _text(entry, "ValDt", "Dt") or _text(entry, "ValDt", "DtTm")
        value_date = date.fromisoformat(value_raw[:10]) if value_raw else None
    except ValueError as exc:
        raise ImportParseError("invalid_date") from exc
    if len(currency) != 3:
        raise ImportParseError("invalid_currency")
    counterparty, identifier = _party(detail, sign)
    purposes = [" ".join((node.text or "").split()) for node in _desc(detail, "Ustrd") if node.text]
    reference = (
        _first_desc_text(detail, "AcctSvcrRef")
        or _first_desc_text(entry, "AcctSvcrRef")
        or _first_desc_text(detail, "EndToEndId")
    )
    return NormalizedRecord(
        source_line=source_line,
        booking_date=booking_date,
        value_date=value_date,
        amount_minor=_minor(amount_node.text, sign),
        currency=currency,
        counterparty=counterparty,
        purpose=" ".join(purposes) or None,
        counterparty_identifier=identifier,
        bank_reference=normalize_bank_reference(reference),
    )


def parse_camt(data: bytes) -> list[NormalizedRecord]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportParseError("invalid_xml_encoding") from exc
    if _FORBIDDEN_XML.search(text):
        raise ImportParseError("xml_declaration_forbidden")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ImportParseError("invalid_xml") from exc
    namespace = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    contracts = _children(root, "BkToCstmrStmt") if _local(root) == "Document" else []
    if namespace not in _ALLOWED_NAMESPACES:
        raise ImportParseError("unsupported_camt_version")
    if len(contracts) != 1:
        raise ImportParseError("invalid_camt_contract")

    records: list[NormalizedRecord] = []
    for entry in _desc(contracts[0], "Ntry"):
        details = _desc(entry, "TxDtls") or [entry]
        entry_amount = next(iter(_children(entry, "Amt")), None)
        entry_start = len(records)
        for detail in details:
            source_line = len(records) + 1
            if source_line > MAX_RECORDS:
                raise ImportParseError("too_many_records")
            try:
                records.append(
                    _parse_detail(
                        entry,
                        detail,
                        entry_amount,
                        source_line,
                        allow_entry_amount=len(details) == 1,
                    )
                )
            except ImportParseError as exc:
                records.append(
                    NormalizedRecord(
                        source_line=source_line,
                        booking_date=None,
                        value_date=None,
                        amount_minor=None,
                        currency=None,
                        errors=(str(exc),),
                    )
                )
        entry_records = records[entry_start:]
        if len(details) > 1 and entry_amount is not None and entry_amount.text:
            sign = _text(entry, "CdtDbtInd") or "CRDT"
            expected = _minor(entry_amount.text, sign)
            actual = sum(row.amount_minor or 0 for row in entry_records)
            if any(row.errors for row in entry_records) or actual != expected:
                records[entry_start:] = [
                    replace(
                        row,
                        errors=tuple(dict.fromkeys((*row.errors, "camt_batch_amount_mismatch"))),
                    )
                    for row in entry_records
                ]
    return records
