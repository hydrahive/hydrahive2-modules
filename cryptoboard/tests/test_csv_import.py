"""CSV-Import-Engine — reine Parse-/Heuristik-Logik (keine DB/Netz)."""
from __future__ import annotations

import pytest

from backend import csv_import as ci


# ---------------------------------------------------------------- sniff
def test_sniff_komma():
    text = "Date,Type,Asset,Amount,Price\n2026-01-01,Buy,BTC,0.5,40000"
    header, rows = ci.sniff(text)
    assert header == ["Date", "Type", "Asset", "Amount", "Price"]
    assert len(rows) == 1
    assert rows[0]["Asset"] == "BTC"


def test_sniff_semikolon():
    text = "Datum;Typ;Währung;Menge;Preis\n01.01.2026;Kauf;ETH;2;3000"
    header, rows = ci.sniff(text)
    assert header[0] == "Datum"
    assert rows[0]["Menge"] == "2"


def test_sniff_bom_und_leerzeilen():
    text = "\ufeffDate,Asset,Amount\n2026-01-01,BTC,1\n\n2026-01-02,ETH,2\n"
    header, rows = ci.sniff(text)
    assert header[0] == "Date"
    assert len(rows) == 2


def test_sniff_leer_wirft():
    with pytest.raises(ci.ImportError):
        ci.sniff("")


def test_sniff_nur_header_wirft():
    with pytest.raises(ci.ImportError):
        ci.sniff("Date,Asset,Amount")


# ---------------------------------------------------------------- guess_map
def test_guess_map_englisch():
    header = ["Date", "Type", "Asset", "Amount", "Price", "Fee"]
    m = ci.guess_map(header)
    assert m["executed_at"] == "Date"
    assert m["kind"] == "Type"
    assert m["symbol"] == "Asset"
    assert m["quantity"] == "Amount"
    assert m["price"] == "Price"
    assert m["fee"] == "Fee"


def test_guess_map_deutsch():
    header = ["Datum", "Typ", "Währung", "Menge", "Kurs", "Gebühr"]
    m = ci.guess_map(header)
    assert m["executed_at"] == "Datum"
    assert m["symbol"] == "Währung"
    assert m["quantity"] == "Menge"
    assert m["price"] == "Kurs"


def test_guess_map_keine_doppelzuordnung():
    # "Amount" darf nicht gleichzeitig quantity UND price sein
    header = ["Date", "Amount", "Price"]
    m = ci.guess_map(header)
    assert m["quantity"] == "Amount"
    assert m["price"] == "Price"


# ---------------------------------------------------------------- parse_number
@pytest.mark.parametrize("raw,expected", [
    ("1234.56", 1234.56),
    ("1.234,56", 1234.56),     # DE
    ("1,234.56", 1234.56),     # EN
    ("1234,56", 1234.56),      # nur Komma
    ("€ 40.000,00", 40000.0),  # Währungssymbol
    ("0.00000123", 0.00000123),
    ("-5,5", -5.5),
    ("", None),
    ("abc", None),
])
def test_parse_number(raw, expected):
    assert ci.parse_number(raw) == expected


# ---------------------------------------------------------------- parse_date
@pytest.mark.parametrize("raw,expected", [
    ("2026-01-15", "2026-01-15"),
    ("2026-01-15T14:30:00", "2026-01-15"),
    ("15.01.2026 14:30", "2026-01-15"),
    ("15/01/2026", "2026-01-15"),
    ("2026-01-15T14:30:00Z", "2026-01-15"),
    ("2026-01-15T14:30:00+01:00", "2026-01-15"),
    ("garbage", None),
    ("", None),
])
def test_parse_date(raw, expected):
    assert ci.parse_date(raw) == expected


# ---------------------------------------------------------------- classify_kind
@pytest.mark.parametrize("raw,expected", [
    ("Buy", "buy"),
    ("Kauf", "buy"),
    ("SELL", "sell"),
    ("Verkauf", "sell"),
    ("Withdrawal", "transfer_out"),
    ("Deposit", "transfer_in"),
    ("", None),
    ("xyz", None),
])
def test_classify_kind(raw, expected):
    assert ci.classify_kind(raw) == expected


# ---------------------------------------------------------------- clean_symbol (über parse_rows)
def test_symbol_aus_pair():
    rows = [{"Asset": "BTC/EUR", "Amount": "1", "Date": "2026-01-01"}]
    mapping = {"symbol": "Asset", "quantity": "Amount", "executed_at": "Date", "kind": None, "price": None, "fee": None}
    out = ci.parse_rows(rows, mapping)
    assert out["transactions"][0]["symbol"] == "BTC"


def test_symbol_angehaengte_quote():
    rows = [{"Asset": "ETHUSDT", "Amount": "2", "Date": "2026-01-01"}]
    mapping = {"symbol": "Asset", "quantity": "Amount", "executed_at": "Date", "kind": None, "price": None, "fee": None}
    out = ci.parse_rows(rows, mapping)
    assert out["transactions"][0]["symbol"] == "ETH"


# ---------------------------------------------------------------- parse_rows
def test_parse_rows_vollstaendig():
    rows = [
        {"Date": "2026-01-01", "Type": "Buy", "Asset": "BTC", "Amount": "0.5", "Price": "40000", "Fee": "10"},
        {"Date": "2026-02-01", "Type": "Sell", "Asset": "BTC", "Amount": "0.2", "Price": "50000", "Fee": "5"},
    ]
    mapping = ci.guess_map(["Date", "Type", "Asset", "Amount", "Price", "Fee"])
    out = ci.parse_rows(rows, mapping)
    assert len(out["transactions"]) == 2
    assert out["transactions"][0]["kind"] == "buy"
    assert out["transactions"][0]["quantity"] == 0.5
    assert out["transactions"][1]["kind"] == "sell"
    assert out["symbols"] == ["BTC"]
    assert out["errors"] == []


def test_parse_rows_fehlerhafte_zeile():
    rows = [
        {"Date": "2026-01-01", "Asset": "BTC", "Amount": "1"},
        {"Date": "", "Asset": "", "Amount": "abc"},  # alles kaputt
    ]
    mapping = {"symbol": "Asset", "quantity": "Amount", "executed_at": "Date", "kind": None, "price": None, "fee": None}
    out = ci.parse_rows(rows, mapping)
    assert len(out["transactions"]) == 1
    assert len(out["errors"]) == 1
    assert out["errors"][0]["row"] == 3  # Header=1, Zeile1=2, Zeile2=3


def test_parse_rows_default_kind():
    rows = [{"Date": "2026-01-01", "Asset": "BTC", "Amount": "1"}]
    mapping = {"symbol": "Asset", "quantity": "Amount", "executed_at": "Date", "kind": None, "price": None, "fee": None}
    out = ci.parse_rows(rows, mapping, default_kind="buy")
    assert out["transactions"][0]["kind"] == "buy"


# ---------------------------------------------------------------- row_hash
def test_row_hash_stabil_und_unterscheidend():
    tx1 = {"kind": "buy", "symbol": "BTC", "quantity": 1.0, "price": 40000, "executed_at": "2026-01-01"}
    tx2 = dict(tx1)
    tx3 = {**tx1, "quantity": 2.0}
    assert ci.row_hash(tx1) == ci.row_hash(tx2)
    assert ci.row_hash(tx1) != ci.row_hash(tx3)
    assert len(ci.row_hash(tx1)) == 32
