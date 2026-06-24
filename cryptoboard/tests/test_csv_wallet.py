"""Regression — Wallet-Bewegungslog im Freewallet-Stil (synthetische Daten).

Prüft das STRUKTUR-Handling: tab-getrennt, negative Beträge als Abgang,
'payout'/'payin'-Typen, Spalte 'Transaction amount' (enthält 'transaction' →
darf NICHT das kind-Feld kapern), viele Nachkomma-Nullen, Zeitzone +0000,
Status-Filter (failed). Alle Werte/IDs sind frei erfunden.
"""
from __future__ import annotations

from backend import csv_import as ci

# Rein synthetisch — keine echten Wallet-Daten. Dummy-IDs/Hashes.
_WALLET = (
    "Date\tTransaction amount\tCurrency\tFee\tTransaction type\tStatus\tRequest id\tTransaction hash\n"
    "2024-01-02T10:00:00+0000\t1234.500000000000000000000000\ttrx\t0\tpayin\tcommitted\tREQ-AAAA\tHASHAAAA\n"
    "2024-02-03T11:00:00+0000\t-200.000000000000000000000000\ttrx\t1\tpayout\tcommitted\tREQ-BBBB\tHASHBBBB\n"
    "2024-02-04T12:00:00+0000\t999.000000000000000000000000\ttrx\t1\tpayout\tfailed\tREQ-CCCC\t\n"
)


def test_wallet_mapping_trifft_richtige_spalten():
    header, _ = ci.sniff(_WALLET)
    m = ci.guess_map(header)
    # 'Transaction amount' MUSS quantity sein, NICHT kind
    assert m["quantity"] == "Transaction amount"
    assert m["kind"] == "Transaction type"
    assert m["symbol"] == "Currency"
    assert m["fee"] == "Fee"
    assert m["executed_at"] == "Date"
    assert m["status"] == "Status"


def test_wallet_payin_ist_zugang_payout_ist_abgang():
    header, rows = ci.sniff(_WALLET)
    out = ci.parse_rows(rows, ci.guess_map(header))
    # payin = Zugang, payout = Abgang; die failed-Zeile ist gefiltert
    assert len(out["transactions"]) == 2
    assert out["skipped_status"] == 1
    payin = out["transactions"][0]
    assert payin["kind"] == "transfer_in"
    assert payin["quantity"] == 1234.5
    assert payin["symbol"] == "TRX"
    payout = out["transactions"][1]
    assert payout["kind"] == "transfer_out"
    assert payout["quantity"] == 200.0


def test_wallet_failed_status_wird_uebersprungen():
    # Eine fehlgeschlagene Transaktion bewegt den Bestand nie → nicht importieren.
    csv = (
        "Date\tTransaction amount\tCurrency\tTransaction type\tStatus\n"
        "2024-03-01T00:00:00+0000\t5000\ttrx\tpayout\tfailed\n"
    )
    header, rows = ci.sniff(csv)
    out = ci.parse_rows(rows, ci.guess_map(header))
    assert out["transactions"] == []
    assert out["skipped_status"] == 1


def test_wallet_rolled_back_status_wird_uebersprungen():
    # rolled_back = zurückgerollt → hat den Bestand per Saldo nie verändert.
    csv = (
        "Date\tTransaction amount\tCurrency\tTransaction type\tStatus\n"
        "2024-01-01T00:00:00+0000\t1000\ttrx\tpayin\tcommitted\n"
        "2024-02-01T00:00:00+0000\t-500\ttrx\tpayout\trolled_back\n"
        "2024-03-01T00:00:00+0000\t-200\ttrx\tpayout\tcommitted\n"
    )
    header, rows = ci.sniff(csv)
    out = ci.parse_rows(rows, ci.guess_map(header))
    # Nur die committed-Zeilen: 1000 rein, 200 raus = 2 Transaktionen
    assert len(out["transactions"]) == 2
    assert out["skipped_status"] == 1  # der rolled_back payout


def test_wallet_positiver_betrag_ohne_typ_wird_zugang():
    csv = (
        "Date\tTransaction amount\tCurrency\tTransaction type\n"
        "2024-01-01T00:00:00+0000\t500.0\ttrx\ttransfer\n"
    )
    header, rows = ci.sniff(csv)
    out = ci.parse_rows(rows, ci.guess_map(header))
    assert out["transactions"][0]["kind"] == "transfer_in"
    assert out["transactions"][0]["quantity"] == 500.0
