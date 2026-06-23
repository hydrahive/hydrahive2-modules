"""CSV-Import-Engine — CSV-Struktur + Mapping, keine DB, kein Netz.

Verarbeitet beliebige Wallet-/Börsen-CSV-Exporte (Option B: generischer Mapper).
Schritte:
  1. sniff()      — Delimiter + Header erkennen, Zeilen als dicts liefern
  2. guess_map()  — Spalten heuristisch auf unsere Felder mappen (DE/EN)
  3. parse_rows() — mit einem (bestätigten) Mapping Transaktionen bauen
  4. row_hash()   — stabiler Dedup-Hash je Transaktion

Die zellweise Wert-Konvertierung (Zahlen/Datum/kind/Symbol) liegt in csv_parse
und wird hier re-exportiert, damit Aufrufer eine Fassade haben.
"""
from __future__ import annotations

import csv
import hashlib
import io

from .csv_parse import classify_kind, clean_symbol, parse_date, parse_number

__all__ = [
    "FIELDS", "ImportError", "sniff", "guess_map", "parse_rows", "row_hash",
    "parse_number", "parse_date", "classify_kind",
]

# Unsere Zielfelder
FIELDS = ("kind", "symbol", "quantity", "price", "fee", "executed_at")

# Heuristik: Header-Schlüsselwörter (lowercase, Teilstring-Match) → Zielfeld.
# WICHTIG: Felder werden in dieser dict-Reihenfolge zugeordnet und eine einmal
# vergebene Spalte ist gesperrt. Darum die SPEZIFISCHEN Felder zuerst (fee/
# quantity/price/date/symbol), kind ZULETZT — sonst kapert ein gieriges
# kind-Hint wie "transaction" die Spalte "Transaction amount".
_HINTS: dict[str, tuple[str, ...]] = {
    "fee": ("fee", "gebühr", "gebuehr", "commission", "provision"),
    "quantity": ("amount", "quantity", "menge", "qty", "anzahl", "units", "volume", "stück", "stueck", "betrag"),
    "price": ("price", "preis", "kurs", "rate", "unit price", "stückpreis", "stueckpreis"),
    "executed_at": ("date", "datum", "time", "zeit", "timestamp", "executed", "created", "filled"),
    "symbol": ("symbol", "asset", "coin", "currency", "währung", "wahrung", "token", "pair", "markt", "market"),
    "status": ("status", "state", "zustand"),
    "kind": ("type", "typ", "side", "art", "operation", "richtung", "buy/sell", "direction"),
}

# Status-Werte, die eine NICHT durchgeführte Transaktion bedeuten → übersprungen.
# (z.B. fehlgeschlagene/abgebrochene Auszahlungen, die nie den Bestand bewegten.)
_BAD_STATUS = ("failed", "fehlgeschlagen", "cancelled", "canceled", "storniert",
               "pending", "rejected", "abgelehnt", "error", "declined", "expired")

_MAX_ROWS = 5000


class ImportError(ValueError):
    """Fachlicher Importfehler (z.B. leeres/unlesbares CSV)."""


# --------------------------------------------------------------------- sniff
def sniff(text: str) -> tuple[list[str], list[dict]]:
    """Erkennt Delimiter, liefert (header, rows-als-dicts). Limitiert Zeilen."""
    text = text.lstrip("\ufeff").strip()
    if not text:
        raise ImportError("empty_csv")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        first = text.splitlines()[0]
        delimiter = max(",;\t|", key=lambda d: first.count(d))

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if len(rows) < 2:
        raise ImportError("no_data_rows")
    header = [h.strip() for h in rows[0]]
    out: list[dict] = []
    for raw in rows[1 : 1 + _MAX_ROWS]:
        if not any(c.strip() for c in raw):
            continue
        out.append({header[i]: (raw[i] if i < len(raw) else "") for i in range(len(header))})
    return header, out


# ----------------------------------------------------------------- guess_map
def guess_map(header: list[str]) -> dict[str, str | None]:
    """Schlägt pro Zielfeld die best-passende CSV-Spalte vor (oder None)."""
    used: set[str] = set()
    mapping: dict[str, str | None] = {}
    for field, hints in _HINTS.items():
        match = None
        for col in header:
            if col in used:
                continue
            if any(h in col.lower() for h in hints):
                match = col
                break
        if match:
            used.add(match)
        mapping[field] = match
    return mapping


# ----------------------------------------------------------------- parse_rows
def parse_rows(rows: list[dict], mapping: dict[str, str | None], default_kind: str = "buy") -> dict:
    """Wendet das Mapping an und liefert {transactions, errors, symbols}.

    Jede Transaktion: kind, symbol, quantity, price, fee, executed_at, hash.
    Zeilen ohne Menge/Symbol/Datum landen als Fehler (mit Zeilennummer).
    """
    col_kind = mapping.get("kind")
    col_symbol = mapping.get("symbol")
    col_qty = mapping.get("quantity")
    col_price = mapping.get("price")
    col_fee = mapping.get("fee")
    col_date = mapping.get("executed_at")
    col_status = mapping.get("status")

    txs: list[dict] = []
    errors: list[dict] = []
    symbols: set[str] = set()
    skipped_status = 0

    for i, row in enumerate(rows, start=2):  # Zeile 1 = Header
        # Nicht durchgeführte Transaktionen (failed/cancelled/…) überspringen —
        # sie haben den Bestand nie bewegt. Kein Fehler, nur ignoriert.
        if col_status:
            st = str(row.get(col_status, "")).strip().lower()
            if any(bad in st for bad in _BAD_STATUS):
                skipped_status += 1
                continue

        symbol = clean_symbol(row.get(col_symbol, "")) if col_symbol else ""
        qty_raw = parse_number(row.get(col_qty, "")) if col_qty else None
        price = parse_number(row.get(col_price, "")) if col_price else 0.0
        fee = parse_number(row.get(col_fee, "")) if col_fee else 0.0
        date = parse_date(row.get(col_date, "")) if col_date else None
        kind = classify_kind(row.get(col_kind, "")) if col_kind else None

        # Vorzeichen = Richtung: Wallet-Logs nutzen -Betrag für Abgang, +Betrag
        # für Zugang. Menge ist immer der Betrag (abs). Ist der Typ nicht als
        # buy/sell erkannt, leitet das Vorzeichen die Transfer-Richtung ab —
        # bei reinen Bewegungslogs ist transfer_in/out die neutrale Wahrheit
        # (kein „Gratis-Kauf", der bei späterem Verkauf voll als Gewinn zählt).
        qty = abs(qty_raw) if qty_raw is not None else None
        if kind is None:
            if qty_raw is not None and qty_raw < 0:
                kind = "transfer_out"
            elif qty_raw is not None:
                kind = "transfer_in"
            else:
                kind = default_kind

        problems = []
        if not symbol:
            problems.append("symbol")
        if qty is None or qty <= 0:
            problems.append("quantity")
        if not date:
            problems.append("date")
        if problems:
            errors.append({"row": i, "missing": problems})
            continue

        tx = {
            "kind": kind, "symbol": symbol, "quantity": qty,
            "price": price or 0.0, "fee": fee or 0.0, "executed_at": date,
        }
        tx["hash"] = row_hash(tx)
        symbols.add(symbol)
        txs.append(tx)

    return {
        "transactions": txs, "errors": errors, "symbols": sorted(symbols),
        "skipped_status": skipped_status,
    }


# ------------------------------------------------------------------ row_hash
def row_hash(tx: dict) -> str:
    """Stabiler Dedup-Hash aus den wertbestimmenden Feldern."""
    key = "|".join(str(tx.get(k, "")) for k in ("kind", "symbol", "quantity", "price", "executed_at"))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
