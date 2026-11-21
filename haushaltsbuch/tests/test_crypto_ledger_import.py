"""Tests für den Crypto-Ledger-Import (Etappe B, VERTRAG-B.md): Vorschau aus
dem Cryptoboard-Ledger (Read-Port v3 `ledger_moves`), Gruppen mit Anzahl/
Summe, Dedup, Buchung erst nach complete.

Fixture (Vertrag): 2 Swaps (Tron->Base), 3 Kartenzahlungen (Base), 1 Abgang
(Ethereum), 1 unklar (fehlendes Swap-Bein). Nutzt denselben Fake-Port wie
test_crypto_bridge.py (monkeypatch von `crypto_bridge._load_port`).
"""

from __future__ import annotations

from backend import crypto_bridge
from conftest import PREFIX
from test_crypto_bridge import FakePort, _install_fake_port
from test_v1_api import _create_account, _create_household, _expense_category


def _wallet_account(client, headers, name: str) -> dict:
    response = client.post(
        f"{PREFIX}/accounts",
        headers=headers,
        json={"name": name, "type": "wallet", "currency": "EUR", "opening_balance": 0},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _link_addr(client, headers, account: dict, address_ids: list[int]) -> dict:
    response = client.put(
        f"{PREFIX}/accounts/{account['id']}/crypto-addresses",
        headers=headers,
        json={"address_ids": address_ids, "revision": account["revision"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _setup_three_wallets(client, headers, port):
    """Tron-Konto (Adresse 3/tron), Base-Konto (Adresse 2/base),
    Ethereum-Konto (Adresse 7/ethereum) - wie Tills echte Konten 4/5/6."""
    _create_household(client, headers)
    tron = _wallet_account(client, headers, "Tron")
    base = _wallet_account(client, headers, "Base")
    ethereum = _wallet_account(client, headers, "Ethereum")
    port.addresses["owner"] = [
        {"id": 2, "chain": "base", "address": "0xbase", "label": "Base"},
        {"id": 3, "chain": "tron", "address": "Ttron", "label": "Tron"},
        {"id": 7, "chain": "ethereum", "address": "0xeth", "label": "Ethereum"},
    ]
    tron = _link_addr(client, headers, tron, [3])
    base = _link_addr(client, headers, base, [2])
    ethereum = _link_addr(client, headers, ethereum, [7])
    return tron, base, ethereum


def _fixture_moves() -> list[dict]:
    """2 Swaps Tron->Base, 3 Kartenzahlungen Base, 1 Abgang Ethereum, 1 unklar."""
    moves = []
    for i in range(2):
        moves.append({
            "type": "swap", "id": f"xchain:tron{i}:base:evm{i}",
            "executed_at": f"2026-0{i + 1}-10T10:00:00Z",
            "from": {"chain": "tron", "symbol": "TRX", "coin_id": "tron", "quantity": "1000",
                      "gross_minor": 5000, "fee_minor": 0, "ref": f"cb:tron{i}"},
            "to": {"chain": "base", "symbol": "USDC", "coin_id": "usd-coin", "quantity": "50.00",
                    "ref": f"cb:base{i}"},
            "value_minor": 5000 + i,
        })
    for i in range(3):
        moves.append({
            "type": "kartenzahlung", "id": f"base:0xkarte{i}:transfer_out",
            "executed_at": f"2026-03-1{i}T12:00:00Z", "chain": "base",
            "symbol": "USDC", "coin_id": "usd-coin", "quantity": "20.00",
            "value_minor": 2000 + i, "ref": f"cb:karte{i}",
        })
    moves.append({
        "type": "abgang", "id": "ethereum:0xabgang:transfer_out",
        "executed_at": "2026-04-01T09:00:00Z", "chain": "ethereum",
        "symbol": "USDC", "coin_id": "usd-coin", "quantity": "9.06",
        "value_minor": 906, "ref": "cb:abgang",
    })
    moves.append({
        "type": "unklar", "id": "xchain:tron9:fehlt", "reason": "swap_bein_fehlt",
    })
    return moves


def _import(client, headers):
    return client.post(f"{PREFIX}/crypto-bridge/ledger-imports", headers=headers, json={})


def test_preview_groups_swaps_kartenzahlungen_abgaenge_unklar(client, owner_headers, monkeypatch):
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()

    response = _import(client, owner_headers)
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["status"] == "draft"
    assert batch["source_format"] == "crypto_ledger"

    groups = batch["groups"]
    assert groups["swaps"] == {"count": 2, "sum_minor": 5000 + 5001}
    assert groups["kartenzahlungen"] == {"count": 3, "sum_minor": 2000 + 2001 + 2002}
    assert groups["abgaenge"] == {"count": 1, "sum_minor": 906}
    assert groups["duplicates"] == 0
    assert len(groups["unklar"]) == 1
    assert groups["unklar"][0]["reason"] == "swap_bein_fehlt"

    rows = batch["rows"]
    assert len(rows) == 7  # 2 swap + 3 kartenzahlung + 1 abgang + 1 unklar
    abgang_row = next(row for row in rows if row["bank_reference"] == "ethereum:0xabgang:transfer_out")
    assert abgang_row["status"] == "rejected"  # standardmäßig ausgeschlossen
    swap_row = next(row for row in rows if row["bank_reference"] == "xchain:tron0:base:evm0")
    assert swap_row["counter_account_id"] is not None
    assert swap_row["category_id"] is None
    assert swap_row["status"] == "pending"
    karte_row = next(row for row in rows if row["bank_reference"] == "base:0xkarte0:transfer_out")
    assert karte_row["counter_account_id"] is None
    assert karte_row["category_id"] is None
    assert karte_row["status"] == "pending"
    unklar_row = next(row for row in rows if row["bank_reference"] == "xchain:tron9:fehlt")
    assert unklar_row["status"] == "error"

    # Nichts gebucht, bis complete explizit aufgerufen wird.
    transactions = client.get(f"{PREFIX}/transactions", headers=owner_headers).json()
    assert transactions == []


def test_second_import_is_fully_duplicate(client, owner_headers, monkeypatch):
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()

    first = _import(client, owner_headers).json()
    assert first["groups"]["swaps"]["count"] == 2

    second = _import(client, owner_headers).json()
    assert second["groups"]["swaps"]["count"] == 0
    assert second["groups"]["kartenzahlungen"]["count"] == 0
    assert second["groups"]["abgaenge"]["count"] == 0
    assert second["groups"]["duplicates"] == 6  # alle buchbaren Zeilen (nicht "unklar")


def test_complete_books_two_transfers_and_three_expenses_not_the_abgang(
    client, owner_headers, monkeypatch
):
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    tron, base, _ethereum = _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()
    batch = _import(client, owner_headers).json()

    for row in batch["rows"]:
        if row["status"] != "pending":
            continue
        patched = client.patch(
            f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
            headers=owner_headers,
            json={"revision": row["revision"], "status": "accepted"},
        )
        assert patched.status_code == 200, patched.text

    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert completed.status_code == 200, completed.text
    imported_rows = [row for row in completed.json()["rows"] if row["status"] == "imported"]
    assert len(imported_rows) == 5  # 2 Umbuchungen + 3 Ausgaben, NICHT der Abgang

    accounts = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()
    tron_after = next(item for item in accounts if item["id"] == tron["id"])
    base_after = next(item for item in accounts if item["id"] == base["id"])
    assert tron_after["balance_base"] == -(5000 + 5001)
    # Base bekommt die Swap-Gegenbuchung (+5000+5001) und zahlt die 3 Kartenzahlungen ab
    assert base_after["balance_base"] == (5000 + 5001) - (2000 + 2001 + 2002)

    no_category = next(
        item for item in client.get(f"{PREFIX}/categories", headers=owner_headers).json()
        if item["name"] == "Ohne Kategorie"
    )
    assert no_category["internal"] is True
    karte_tx = client.get(
        f"{PREFIX}/transactions/"
        f"{next(r for r in imported_rows if r['bank_reference'] == 'base:0xkarte0:transfer_out')['transaction_id']}",
        headers=owner_headers,
    ).json()
    assert {p["category_id"] for p in karte_tx["postings"] if p["category_id"]} == {no_category["id"]}


def test_without_complete_nothing_is_booked(client, owner_headers, monkeypatch):
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()
    batch = _import(client, owner_headers).json()
    for row in batch["rows"]:
        if row["status"] == "pending":
            client.patch(
                f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
                headers=owner_headers,
                json={"revision": row["revision"], "status": "accepted"},
            )
    # complete NICHT aufgerufen.
    assert client.get(f"{PREFIX}/transactions", headers=owner_headers).json() == []


def test_port_v2_is_fail_closed(client, owner_headers, monkeypatch):
    """Ein noch nicht auf v3 aktualisierter Port (Konto bereits verknüpft,
    aber _load_port() liefert jetzt wieder v2) -> fail-closed, kein
    Rückfall auf die alten ledger-Funktionen."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)

    def _raise_incompatible():
        raise crypto_bridge.CryptoBridgeUnavailable("port_incompatible")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_incompatible)
    response = _import(client, owner_headers)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "crypto_bridge_unavailable"
    assert detail["params"]["reason"] == "port_incompatible"


# ---------------------------------------------------------------------------
# Gegenproben
# ---------------------------------------------------------------------------


def test_counterproof_swap_as_category_posting_would_count_as_expense(
    client, owner_headers, monkeypatch
):
    """Gegenprobe zu B1: Würde man einen Swap-Betrag (statt als Transfer
    über counter_account_id) wie eine normale Ausgabe MIT Kategorie buchen,
    zählte er im Cashflow-/Kategorien-Report als Ausgabe. Das belegt, dass
    unser Swap NUR deshalb nicht als Ausgabe zählt, weil import_completion
    ihn über counter_account_id (zwei Konto-Postings, keine Kategorie) statt
    über eine Kategorie bucht - nicht weil der Betrag zufällig klein ist."""
    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    category = _expense_category(client, owner_headers)
    manual = client.post(
        f"{PREFIX}/transactions",
        headers=owner_headers,
        json={
            "booking_date": "2026-01-10", "source": "manual",
            "postings": [
                {"account_id": account["id"], "original_amount": -5000, "currency": "EUR", "base_amount": -5000},
                {"category_id": category["id"], "original_amount": 5000, "currency": "EUR", "base_amount": 5000},
            ],
        },
    )
    assert manual.status_code == 201, manual.text
    cashflow = client.get(f"{PREFIX}/reports/cashflow?range=24", headers=owner_headers).json()
    assert sum(row["expense"] for row in cashflow["rows"]) == 5000


def test_counterproof_non_crypto_ledger_import_still_requires_category(
    client, owner_headers, monkeypatch
):
    """Gegenprobe: Der normale Datei-Import (CSV) verlangt weiterhin eine
    Kategorie - 'Ohne Kategorie' gilt NUR für crypto_ledger."""
    import json

    _create_household(client, owner_headers)
    account = _create_account(client, owner_headers, opening_balance=0)
    mapping = {
        "booking_date": "Buchungstag", "amount": "Betrag", "currency": "Waehrung",
        "delimiter": ";", "encoding": "utf-8", "decimal_separator": ",", "date_format": "%d.%m.%Y",
    }
    csv_content = (
        "Buchungstag;Betrag;Waehrung;Name;Verwendungszweck;Referenz\n"
        "01.03.2026;-12,00;EUR;Supermarkt;Einkauf;ref-1\n"
    ).encode("utf-8")
    upload = client.post(
        f"{PREFIX}/imports",
        headers=owner_headers,
        files={"file": ("umsatz.csv", csv_content, "text/csv")},
        data={"account_id": str(account["id"]), "format": "csv", "mapping": json.dumps(mapping)},
    )
    assert upload.status_code == 201, upload.text
    batch = upload.json()
    row = batch["rows"][0]
    patched = client.patch(
        f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
        headers=owner_headers,
        json={"revision": row["revision"], "status": "accepted"},
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert completed.status_code == 422
    assert completed.json()["detail"]["code"] == "import_category_required"


def test_counterproof_duplicate_dedup_off_would_show_as_new(client, owner_headers, monkeypatch):
    """Gegenprobe zur Dedup-Logik: unterschiedliche Cryptoboard-ids (kein
    echtes Duplikat) erzeugen KEINE Duplicate-Markierung - stellt sicher,
    dass der Dedup-Test oben wirklich die ID prüft und nicht zufällig
    alles als Duplikat markiert."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()[:1]
    first = _import(client, owner_headers).json()
    assert first["groups"]["duplicates"] == 0

    different_moves = _fixture_moves()[:1]
    different_moves[0]["id"] = "xchain:tron0:base:evm0:andere-id"
    different_moves[0]["from"]["ref"] = "cb:tron0:andere-id"
    different_moves[0]["to"]["ref"] = "cb:base0:andere-id"
    port.ledger_moves_data["owner"] = different_moves
    second = _import(client, owner_headers).json()
    assert second["groups"]["duplicates"] == 0
    assert second["groups"]["swaps"]["count"] == 1


def test_counterproof_report_categories_excludes_swap_includes_kartenzahlung(
    client, owner_headers, monkeypatch
):
    """Belegt B1/D2: Swaps (kein category_id) zählen NICHT im
    Kategorien-Report, die Kartenzahlung (System-Kategorie) schon."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()
    batch = _import(client, owner_headers).json()
    for row in batch["rows"]:
        if row["status"] == "pending":
            client.patch(
                f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
                headers=owner_headers,
                json={"revision": row["revision"], "status": "accepted"},
            )
    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    ).json()

    cashflow = client.get(f"{PREFIX}/reports/cashflow?range=24", headers=owner_headers).json()
    total_expense = sum(row["expense"] for row in cashflow["rows"])
    # Nur die 3 Kartenzahlungen sind Ausgaben (Swaps zählen nicht mit).
    assert total_expense == 2000 + 2001 + 2002

    categories_report = client.get(
        f"{PREFIX}/reports/categories?range=24", headers=owner_headers
    ).json()
    no_category_row = next(
        row for row in categories_report["rows"] if row["name"] == "Ohne Kategorie"
    )
    assert no_category_row["amount"] == 2000 + 2001 + 2002
    imported_count = sum(1 for row in completed["rows"] if row["status"] == "imported")
    assert imported_count == 5


def _accept_all_and_complete(client, headers, batch: dict) -> None:
    for row in batch["rows"]:
        if row["status"] != "pending":
            continue
        patched = client.patch(f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}", headers=headers,
                               json={"revision": row["revision"], "status": "accepted"})
        assert patched.status_code == 200, patched.text
    done = client.post(f"{PREFIX}/imports/{batch['id']}/complete", headers=headers,
                       json={"revision": batch["revision"]})
    assert done.status_code == 200, done.text


def test_second_import_after_accept_and_complete_is_fully_duplicate(client, owner_headers, monkeypatch):
    """Live-Probe 21.11.2026: Nach Annehmen + Buchen kamen beim zweiten Import alle
    Kartenzahlungen (Base-Konto, Batch auf Tron-Konto) erneut als neu - update_row bildete
    die Kennung über das Batch-Konto statt über das Konto der Zeile."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()

    _accept_all_and_complete(client, owner_headers, _import(client, owner_headers).json())
    second = _import(client, owner_headers).json()
    assert second["groups"]["kartenzahlungen"]["count"] == 0
    assert second["groups"]["swaps"]["count"] == 0
    assert not [r for r in second["rows"] if r["status"] == "pending"]


def test_payment_below_one_cent_is_unklar_not_pending(client, owner_headers, monkeypatch):
    """0,002466 USDC -> 0 Cent: als Buchung nicht annehmbar, darum sichtbar 'unklar'."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    tiny = {"type": "kartenzahlung", "id": "base:0xtiny:transfer_out", "executed_at": "2026-11-05T10:00:00Z",
            "chain": "base", "symbol": "USDC", "coin_id": "usd-coin", "quantity": "0.002466",
            "value_minor": 0, "ref": "cb:tiny"}
    port.ledger_moves_data["owner"] = [*_fixture_moves(), tiny]
    groups = _import(client, owner_headers).json()["groups"]
    assert groups["kartenzahlungen"]["count"] == 3
    assert {"id": "base:0xtiny:transfer_out", "reason": "betrag_unter_1_cent"} in groups["unklar"]


def test_accept_all_suggestions_never_rebooks_duplicates(client, owner_headers, monkeypatch):
    """Till 21.11.2026 (Batch 6): Vorschlagen + „Alle Vorschläge übernehmen“ setzte die 17 schon
    gebuchten Swaps (Status 'duplicate') auf 'accepted' -> zweites Mal gebucht."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    tron, base, _eth = _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()
    _accept_all_and_complete(client, owner_headers, _import(client, owner_headers).json())
    tron_before = next(a for a in client.get(f"{PREFIX}/accounts", headers=owner_headers).json() if a["id"] == tron["id"])

    port.ledger_moves_data["owner"] = [*_fixture_moves(), {
        "type": "kartenzahlung", "id": "base:0xneu:transfer_out", "executed_at": "2026-05-01T12:00:00Z",
        "chain": "base", "symbol": "USDC", "coin_id": "usd-coin", "quantity": "5", "value_minor": 500, "ref": "cb:neu"}]
    batch = _import(client, owner_headers).json()
    sonstiges = _expense_category(client, owner_headers)

    async def _alles_sonstiges(messages, **_kw):
        import json as _json
        keys = [line.split(" :: ")[0] for line in messages[-1]["content"].splitlines() if " :: " in line]
        return _json.dumps([{"id": k, "category_id": sonstiges["id"], "confidence": 0.9} for k in keys])

    monkeypatch.setattr("backend.categorize_llm.complete", _alles_sonstiges)
    assert client.post(f"{PREFIX}/imports/{batch['id']}/suggest-categories", headers=owner_headers, json={}).status_code == 200
    rev = client.get(f"{PREFIX}/imports/{batch['id']}", headers=owner_headers).json()["revision"]
    accepted = client.post(f"{PREFIX}/imports/{batch['id']}/accept-suggestions", headers=owner_headers,
                           json={"revision": rev}).json()
    assert not [r for r in accepted["rows"] if r["status"] == "accepted" and r["bank_reference"].startswith("xchain:")]

    tron_after = next(a for a in client.get(f"{PREFIX}/accounts", headers=owner_headers).json() if a["id"] == tron["id"])
    assert tron_after["balance_base"] == tron_before["balance_base"]


def test_complete_refuses_row_already_booked_elsewhere(client, owner_headers, monkeypatch):
    """Letzte Sicherung: auch wenn eine schon gebuchte Kennung auf 'accepted' steht, wird nicht gebucht."""
    port = FakePort()
    _install_fake_port(monkeypatch, port)
    _setup_three_wallets(client, owner_headers, port)
    port.ledger_moves_data["owner"] = _fixture_moves()
    _accept_all_and_complete(client, owner_headers, _import(client, owner_headers).json())
    second = _import(client, owner_headers).json()
    from hydrahive.db.connection import db as _db
    with _db() as conn:   # simuliert einen alten/fremden Weg, der 'duplicate' auf 'accepted' setzt
        conn.execute("UPDATE module_haushaltsbuch_import_rows SET status='accepted' WHERE batch_id=? AND status='duplicate'",
                     (second["id"],))
    done = client.post(f"{PREFIX}/imports/{second['id']}/complete", headers=owner_headers,
                       json={"revision": second["revision"]})
    assert done.status_code == 409 and done.json()["detail"]["code"] == "duplicate_import_row"
