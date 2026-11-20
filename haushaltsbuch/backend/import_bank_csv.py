"""Bank-Vorlagen für die feste CSV-Erkennung per Kopfzeile (kein LLM, kein Raten).

Vertrag: hb-bank-csv-notes.md. Spaltenaufbauten belegt über
github.com/nicolettas-muggelbude/RechnungsFee/blob/main/vorlagen/bank-csv/README.md
(Stand 20.11.2026) + Prüfung der dort verlinkten Beispieldateien.

Diese Datei enthält nur die Vorlagen (BankTemplate) und die Normalisierung der
Spaltennamen (BOM/Anführungszeichen weg, Umlaute -> ae/oe/ue/ss,
Mehrfach-Leerzeichen -> 1 Leerzeichen) - die eigentliche Erkennung/Umschreibung
ist in import_bank_csv_rewrite.py (Dateigrößenlimit)."""

from __future__ import annotations

import re
from dataclasses import dataclass


def normalize_header_name(name: str) -> str:
    """BOM/Anführungszeichen weg, Umlaute transliteriert, auf 1 Leerzeichen
    reduziert, klein geschrieben - macht Spaltennamen über Bank-Varianten
    vergleichbar (z.B. "Begünstigter" und "Beguenstigter" werden gleich)."""
    name = name.lstrip("\ufeff").strip().strip('"').strip("'").strip()
    name = (
        name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("€", "eur")
    )
    return re.sub(r"\s+", " ", name).strip().casefold()


@dataclass(frozen=True, slots=True)
class BankTemplate:
    id: str
    label: str
    header: tuple[str, ...]  # bereits normalisiert
    mapping: dict  # CsvMapping-kwargs, Werte = normalisierte Spaltennamen
    pending_column: str | None = None  # normalisierter Spaltenname
    pending_values: tuple[str, ...] = ()  # normalisierte Werte -> pending_transaction
    skip_zero_amount: bool = False  # Zeilen mit Betrag 0 sind Bank-Infotext, keine Buchung
    dkb_counterparty: bool = False  # Gegenpartei je Richtung zusammenführen (status/umsatztyp)


TEMPLATES: tuple[BankTemplate, ...] = (
    BankTemplate(
        id="sparkasse_mt940", label="Sparkasse – CSV-MT940",
        header=(
            "auftragskonto", "buchungstag", "valutadatum", "buchungstext", "verwendungszweck",
            "beguenstigter/zahlungspflichtiger", "kontonummer", "blz", "betrag", "waehrung", "info",
        ),
        mapping=dict(
            booking_date="buchungstag", value_date="valutadatum", amount="betrag", currency="waehrung",
            counterparty="beguenstigter/zahlungspflichtiger", purpose="verwendungszweck", date_format="%d.%m.%y",
        ),
        pending_column="info", pending_values=("umsatz vorgemerkt",),
    ),
    BankTemplate(
        id="sparkasse_camt", label="Sparkasse – CSV-CAMT",
        header=(
            "auftragskonto", "buchungstag", "valutadatum", "buchungstext", "verwendungszweck",
            "glaeubiger id", "mandatsreferenz", "kundenreferenz (end-to-end)", "sammlerreferenz",
            "lastschrift ursprungsbetrag", "auslagenersatz ruecklastschrift",
            "beguenstigter/zahlungspflichtiger", "kontonummer/iban", "bic (swift-code)", "betrag",
            "waehrung", "info",
        ),
        mapping=dict(
            booking_date="buchungstag", value_date="valutadatum", amount="betrag", currency="waehrung",
            counterparty="beguenstigter/zahlungspflichtiger", counterparty_identifier="kontonummer/iban",
            purpose="verwendungszweck", bank_reference="mandatsreferenz", date_format="%d.%m.%y",
        ),
        pending_column="info", pending_values=("umsatz vorgemerkt",),
    ),
    BankTemplate(
        id="genossenschaft", label="Volksbank/Raiffeisen/Sparda/GLS",
        header=(
            "bezeichnung auftragskonto", "iban auftragskonto", "bic auftragskonto",
            "bankname auftragskonto", "buchungstag", "valutadatum", "name zahlungsbeteiligter",
            "iban zahlungsbeteiligter", "bic (swift-code) zahlungsbeteiligter", "buchungstext",
            "verwendungszweck", "betrag", "waehrung", "saldo nach buchung", "bemerkung",
            "gekennzeichneter umsatz", "glaeubiger id", "mandatsreferenz",
        ),
        mapping=dict(
            booking_date="buchungstag", value_date="valutadatum", amount="betrag", currency="waehrung",
            counterparty="name zahlungsbeteiligter", counterparty_identifier="iban zahlungsbeteiligter",
            purpose="verwendungszweck", bank_reference="mandatsreferenz", date_format="%d.%m.%Y",
        ),
    ),
    BankTemplate(
        id="ing", label="ING",
        header=(
            "buchung", "wertstellungsdatum", "auftraggeber/empfaenger", "buchungstext",
            "verwendungszweck", "betrag", "waehrung",
        ),
        mapping=dict(
            booking_date="buchung", value_date="wertstellungsdatum", amount="betrag", currency="waehrung",
            counterparty="auftraggeber/empfaenger", purpose="verwendungszweck", date_format="%d.%m.%Y",
        ),
    ),
    BankTemplate(
        id="dkb", label="DKB",
        header=(
            "buchungsdatum", "wertstellung", "status", "zahlungspflichtige*r",
            "zahlungsempfaenger*in", "verwendungszweck", "umsatztyp", "iban", "betrag (eur)",
            "glaeubiger-id", "mandatsreferenz", "kundenreferenz",
        ),
        mapping=dict(
            booking_date="buchungsdatum", value_date="wertstellung", amount="betrag (eur)",
            counterparty="_gegenpartei", purpose="verwendungszweck", bank_reference="mandatsreferenz",
            date_format="%d.%m.%y",
        ),
        pending_column="status", pending_values=("vorgemerkt",), dkb_counterparty=True,
    ),
    BankTemplate(
        id="commerzbank", label="Commerzbank",
        header=(
            "buchungstag", "wertstellung", "umsatzart", "buchungstext", "betrag", "waehrung",
            "iban kontoinhaber", "kategorie",
        ),
        mapping=dict(
            booking_date="buchungstag", value_date="wertstellung", amount="betrag", currency="waehrung",
            purpose="buchungstext", date_format="%d.%m.%Y",
        ),
        skip_zero_amount=True,
    ),
    BankTemplate(
        id="postbank", label="Postbank",
        header=(
            "buchungstag", "wert", "umsatzart", "beguenstigter / auftraggeber", "verwendungszweck",
            "iban / kontonummer", "bic", "kundenreferenz", "mandatsreferenz", "glaeubiger id",
            "fremde gebuehren", "betrag", "abweichender empfaenger", "anzahl der auftraege",
            "anzahl der schecks", "soll", "haben", "waehrung",
        ),
        mapping=dict(
            booking_date="buchungstag", value_date="wert", amount="betrag", currency="waehrung",
            counterparty="beguenstigter / auftraggeber", counterparty_identifier="iban / kontonummer",
            purpose="verwendungszweck", bank_reference="mandatsreferenz", date_format="%d.%m.%Y",
        ),
    ),
)
