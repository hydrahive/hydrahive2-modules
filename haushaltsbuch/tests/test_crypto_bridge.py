"""Tests für die Crypto-Brücke (Phase 3): Verknüpfung, Live-Wert, Trade-Import.

Nutzt ausschließlich einen Fake-Port (monkeypatch von `crypto_bridge._load_port`)
- kein echtes cryptoboard-Modul nötig, wie im Vertrag vorgesehen.
"""

from __future__ import annotations

from datetime import date

from backend import crypto_bridge
from conftest import PREFIX
from test_v1_api import _create_account, _create_household, _expense_category


class FakePortfolioNotFound(LookupError):
    pass


class FakePortfolioUnavailable(RuntimeError):
    pass


class FakePort:
    """Fake-Implementierung des Read-Ports mit demselben Interface wie
    cryptoboard/backend/read_port.py (PORT_VERSION, portfolios_for,
    portfolio_value, trades, PortfolioNotFound, PortfolioUnavailable)."""

    PORT_VERSION = 1
    PortfolioNotFound = FakePortfolioNotFound
    PortfolioUnavailable = FakePortfolioUnavailable

    def __init__(self):
        self.calls: list[tuple[str, str]] = []  # (method, username)
        self.portfolios: dict[str, list[dict]] = {}
        self.values: dict[str, dict] = {}
        self.trade_data: dict[str, list[dict]] = {}
        self.fail_with: Exception | None = None

    def portfolios_for(self, username: str) -> list[dict]:
        self.calls.append(("portfolios_for", username))
        return self.portfolios.get(username, [])

    async def portfolio_value(self, username: str, portfolio_id: str) -> dict:
        self.calls.append(("portfolio_value", username))
        if self.fail_with is not None:
            raise self.fail_with
        if portfolio_id not in {p["id"] for p in self.portfolios.get(username, [])}:
            raise FakePortfolioNotFound(portfolio_id)
        return self.values[username]

    def trades(self, username: str, portfolio_id: str, *, since=None, limit=1000) -> list[dict]:
        self.calls.append(("trades", username))
        if self.fail_with is not None:
            raise self.fail_with
        rows = self.trade_data.get(username, [])
        if since:
            rows = [r for r in rows if r["executed_at"] >= since]
        return rows[:limit]


def _fake_port_version(version: int):
    class _Port(FakePort):
        PORT_VERSION = version

    return _Port()


def _wallet_account(client, headers, *, name="Krypto-Wallet") -> dict:
    response = client.post(
        f"{PREFIX}/accounts",
        headers=headers,
        json={"name": name, "type": "wallet", "currency": "EUR", "opening_balance": 0},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _install_fake_port(monkeypatch, port: FakePort) -> None:
    monkeypatch.setattr(crypto_bridge, "_load_port", lambda: port)


def _link(client, headers, account: dict, portfolio_id: str = "default"):
    return client.put(
        f"{PREFIX}/accounts/{account['id']}/crypto-link",
        headers=headers,
        json={"portfolio_id": portfolio_id, "revision": account["revision"]},
    )


# ---------------------------------------------------------------------------
# Status / Verfügbarkeit
# ---------------------------------------------------------------------------


def test_status_unavailable_module_missing_no_500(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)

    def _raise_missing():
        raise crypto_bridge.CryptoBridgeUnavailable("module_missing")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_missing)
    response = client.get(f"{PREFIX}/crypto-bridge/status", headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == {"available": False, "reason": "module_missing", "portfolios": []}


def test_status_unavailable_module_not_loaded(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)

    def _raise_not_loaded():
        raise crypto_bridge.CryptoBridgeUnavailable("module_not_loaded")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_not_loaded)
    response = client.get(f"{PREFIX}/crypto-bridge/status", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["reason"] == "module_not_loaded"


def test_status_unavailable_port_version_mismatch(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)

    def _raise_incompatible():
        raise crypto_bridge.CryptoBridgeUnavailable("port_incompatible")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_incompatible)
    response = client.get(f"{PREFIX}/crypto-bridge/status", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["reason"] == "port_incompatible"


def test_status_available_returns_own_portfolios(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)

    response = client.get(f"{PREFIX}/crypto-bridge/status", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["portfolios"] == [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    assert port.calls == [("portfolios_for", "owner")]


# ---------------------------------------------------------------------------
# Verknüpfen
# ---------------------------------------------------------------------------


def test_link_requires_wallet_type(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    checking = _create_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)

    response = _link(client, owner_headers, checking)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "crypto_wallet_required"


def test_link_requires_own_portfolio_id(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)

    response = _link(client, owner_headers, wallet, portfolio_id="not-mine")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "crypto_portfolio_not_found"


def test_link_requires_eur(client, owner_headers, monkeypatch):
    # Haushalt mit nicht-EUR Basiswährung -> 422 beim Verknüpfen.
    response = client.post(
        f"{PREFIX}/household",
        headers=owner_headers,
        json={"name": "USD-Haushalt", "base_currency": "USD", "timezone": "Europe/Berlin"},
    )
    assert response.status_code == 201, response.text
    wallet_response = client.post(
        f"{PREFIX}/accounts",
        headers=owner_headers,
        json={"name": "Wallet", "type": "wallet", "currency": "USD", "opening_balance": 0},
    )
    assert wallet_response.status_code == 201, wallet_response.text
    wallet = wallet_response.json()
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)

    response = _link(client, owner_headers, wallet)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "crypto_currency_unsupported"


def test_link_success_and_already_linked_rejected(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)

    linked = _link(client, owner_headers, wallet)
    assert linked.status_code == 200, linked.text
    account = linked.json()
    assert account["linked_portfolio_id"] == "default"
    assert account["linked_by_me"] is True
    assert account["crypto_linked"] is True
    assert account["revision"] == wallet["revision"] + 1

    second = _link(client, owner_headers, account)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "crypto_account_linked"


# ---------------------------------------------------------------------------
# Typwechsel-Sperre
# ---------------------------------------------------------------------------


def test_type_change_away_from_wallet_is_locked_while_linked(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    linked = _link(client, owner_headers, wallet).json()

    response = client.put(
        f"{PREFIX}/accounts/{linked['id']}",
        headers=owner_headers,
        json={
            "name": linked["name"], "type": "checking", "owner_member_id": None,
            "bank_identifier": None, "archived": False, "revision": linked["revision"],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "crypto_account_linked"


# ---------------------------------------------------------------------------
# Manuelle Buchung gesperrt, Import erlaubt
# ---------------------------------------------------------------------------


def test_manual_booking_on_linked_account_is_locked(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    category = _expense_category(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    _link(client, owner_headers, wallet)

    response = client.post(
        f"{PREFIX}/transactions",
        headers=owner_headers,
        json={
            "booking_date": date.today().isoformat(),
            "postings": [
                {"account_id": wallet["id"], "original_amount": -100, "currency": "EUR", "base_amount": -100},
                {"category_id": category["id"], "original_amount": 100, "currency": "EUR", "base_amount": 100},
            ],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "crypto_account_linked"


# ---------------------------------------------------------------------------
# Trennen fällt auf gebuchten Saldo zurück
# ---------------------------------------------------------------------------


def test_unlink_falls_back_to_booked_balance(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    port.values["owner"] = {
        "value_minor": 99999, "as_of": "2026-01-01T00:00:00Z", "complete": True,
    }
    _install_fake_port(monkeypatch, port)
    linked = _link(client, owner_headers, wallet).json()

    value_response = client.get(f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=owner_headers)
    assert value_response.status_code == 200
    assert value_response.json()["state"] == "live"
    assert value_response.json()["booked_balance"] == 0

    unlinked = client.delete(
        f"{PREFIX}/accounts/{linked['id']}/crypto-link?revision={linked['revision']}",
        headers=owner_headers,
    )
    assert unlinked.status_code == 200, unlinked.text
    account = unlinked.json()
    assert account["linked_portfolio_id"] is None
    assert account["crypto_linked"] is False
    assert account["balance_base"] == 0  # gebuchter Saldo unverändert (keine Datenverluste)

    accounts = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()
    reloaded = next(item for item in accounts if item["id"] == linked["id"])
    assert reloaded["balance_base"] == 0


# ---------------------------------------------------------------------------
# live -> Snapshot -> stale
# ---------------------------------------------------------------------------


def test_live_value_updates_snapshot_then_falls_back_to_stale_on_outage(
    client, owner_headers, monkeypatch
):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    port.values["owner"] = {"value_minor": 50000, "as_of": "2026-01-01T00:00:00Z", "complete": True}
    _install_fake_port(monkeypatch, port)
    linked = _link(client, owner_headers, wallet).json()

    live = client.get(f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=owner_headers)
    assert live.status_code == 200
    assert live.json()["state"] == "live"
    assert live.json()["value_minor"] == 50000
    assert type(live.json()["value_minor"]) is int

    # Port fällt aus (z.B. Modul wurde entladen) -> stale mit letztem Snapshot.
    def _raise_missing():
        raise crypto_bridge.CryptoBridgeUnavailable("module_missing")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_missing)
    stale = client.get(f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=owner_headers)
    assert stale.status_code == 200
    body = stale.json()
    assert body["state"] == "stale"
    assert body["value_minor"] == 50000
    assert body["as_of"] == "2026-01-01T00:00:00Z"
    assert body["reason"] == "module_missing"


def test_portfolio_unavailable_falls_back_to_stale(client, owner_headers, monkeypatch):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    port.values["owner"] = {"value_minor": 1234, "as_of": "2026-02-01T00:00:00Z", "complete": True}
    _install_fake_port(monkeypatch, port)
    linked = _link(client, owner_headers, wallet).json()
    client.get(f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=owner_headers)

    port.fail_with = FakePortfolioUnavailable("Kursquelle down")
    stale = client.get(f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=owner_headers)
    assert stale.status_code == 200
    body = stale.json()
    assert body["state"] == "stale"
    assert body["value_minor"] == 1234
    assert body["reason"] is not None


def test_crypto_value_without_any_snapshot_yet_is_stale_with_null_value(
    client, owner_headers, monkeypatch
):
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    linked = _link(client, owner_headers, wallet).json()

    def _raise_missing():
        raise crypto_bridge.CryptoBridgeUnavailable("module_missing")

    monkeypatch.setattr(crypto_bridge, "_load_port", _raise_missing)
    response = client.get(f"{PREFIX}/accounts/{linked['id']}/crypto-value", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "stale"
    assert body["value_minor"] is None
    assert body["as_of"] is None


# ---------------------------------------------------------------------------
# Trade-Import: buy/sell/Gebühr/transfer-Überspringen/Dedup/reverse
# ---------------------------------------------------------------------------


def _setup_linked_wallet_and_fiat(client, headers, port):
    _create_household(client, headers)
    wallet = _wallet_account(client, headers)
    fiat = _create_account(client, headers, opening_balance=0)
    linked = _link(client, headers, wallet).json()
    return linked, fiat


def test_trade_import_buy_sell_fee_split_and_transfer_skipped(client, owner_headers, monkeypatch):
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    wallet, fiat = _setup_linked_wallet_and_fiat(client, owner_headers, port)
    category = _expense_category(client, owner_headers)

    port.trade_data["owner"] = [
        {
            "ref": "cb:1", "kind": "buy", "coin_id": "btc", "symbol": "BTC",
            "quantity": "0.01", "gross_minor": 50000, "fee_minor": 500,
            "executed_at": "2026-01-10T10:00:00Z", "import_hash": None,
        },
        {
            "ref": "cb:2", "kind": "sell", "coin_id": "btc", "symbol": "BTC",
            "quantity": "0.005", "gross_minor": 30000, "fee_minor": 0,
            "executed_at": "2026-01-15T10:00:00Z", "import_hash": None,
        },
        {
            "ref": "cb:3", "kind": "transfer_in", "coin_id": "btc", "symbol": "BTC",
            "quantity": "0.002", "gross_minor": 0, "fee_minor": 0,
            "executed_at": "2026-01-20T10:00:00Z", "import_hash": None,
        },
    ]

    preview = client.post(
        f"{PREFIX}/crypto-bridge/trade-imports",
        headers=owner_headers,
        json={
            "wallet_account_id": wallet["id"], "fiat_account_id": fiat["id"],
            "fee_category_id": category["id"], "since": None,
        },
    )
    assert preview.status_code == 201, preview.text
    batch = preview.json()
    assert batch["status"] == "draft"
    assert batch["source_format"] == "crypto_trades"
    assert batch["account_id"] == fiat["id"]
    assert batch["display_filename"] == "Cryptoboard-Trades"
    assert batch["warnings"]["skipped_transfers"] == 1

    rows = batch["rows"]
    assert len(rows) == 3  # buy-Hauptzeile + buy-Gebühr + sell-Hauptzeile
    assert all(row["status"] == "pending" for row in rows)

    buy_main = next(row for row in rows if row["bank_reference"] == "cb:1")
    assert buy_main["amount_minor"] == -50000
    assert type(buy_main["amount_minor"]) is int
    assert buy_main["counter_account_id"] == wallet["id"]
    assert buy_main["category_id"] is None
    assert "0.01" in buy_main["purpose"]
    assert "BTC" in buy_main["purpose"]

    buy_fee = next(row for row in rows if row["bank_reference"] == "cb:1:fee")
    assert buy_fee["amount_minor"] == -500
    assert buy_fee["category_id"] == category["id"]
    assert buy_fee["counter_account_id"] is None

    sell_main = next(row for row in rows if row["bank_reference"] == "cb:2")
    assert sell_main["amount_minor"] == 30000
    assert sell_main["counter_account_id"] == wallet["id"]

    # Nichts gebucht, bis complete explizit aufgerufen wird.
    transactions = client.get(f"{PREFIX}/transactions", headers=owner_headers).json()
    assert transactions == []


def test_trade_import_complete_creates_transfer_and_fee_postings_then_reverses(
    client, owner_headers, monkeypatch
):
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    wallet, fiat = _setup_linked_wallet_and_fiat(client, owner_headers, port)
    category = _expense_category(client, owner_headers)

    port.trade_data["owner"] = [
        {
            "ref": "cb:buy1", "kind": "buy", "coin_id": "btc", "symbol": "BTC",
            "quantity": "0.01", "gross_minor": 50000, "fee_minor": 500,
            "executed_at": "2026-01-10T10:00:00Z", "import_hash": None,
        },
    ]
    batch = client.post(
        f"{PREFIX}/crypto-bridge/trade-imports",
        headers=owner_headers,
        json={
            "wallet_account_id": wallet["id"], "fiat_account_id": fiat["id"],
            "fee_category_id": category["id"], "since": None,
        },
    ).json()

    for row in batch["rows"]:
        patch_body = {"revision": row["revision"], "status": "accepted"}
        if row["category_id"] is None and row["counter_account_id"] is None:
            patch_body["category_id"] = category["id"]
        patched = client.patch(
            f"{PREFIX}/imports/{batch['id']}/rows/{row['id']}",
            headers=owner_headers,
            json=patch_body,
        )
        assert patched.status_code == 200, patched.text

    completed = client.post(
        f"{PREFIX}/imports/{batch['id']}/complete",
        headers=owner_headers,
        json={"revision": batch["revision"]},
    )
    assert completed.status_code == 200, completed.text
    completed_body = completed.json()
    imported_rows = [row for row in completed_body["rows"] if row["status"] == "imported"]
    assert len(imported_rows) == 2

    transfer_row = next(row for row in imported_rows if row["bank_reference"] == "cb:buy1")
    transfer_tx = client.get(
        f"{PREFIX}/transactions/{transfer_row['transaction_id']}", headers=owner_headers
    ).json()
    posting_accounts = {p["account_id"] for p in transfer_tx["postings"] if p["account_id"]}
    assert posting_accounts == {fiat["id"], wallet["id"]}
    assert sum(p["base_amount"] for p in transfer_tx["postings"]) == 0

    fee_row = next(row for row in imported_rows if row["bank_reference"] == "cb:buy1:fee")
    fee_tx = client.get(
        f"{PREFIX}/transactions/{fee_row['transaction_id']}", headers=owner_headers
    ).json()
    fee_categories = {p["category_id"] for p in fee_tx["postings"] if p["category_id"]}
    assert fee_categories == {category["id"]}

    accounts = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()
    wallet_after = next(item for item in accounts if item["id"] == wallet["id"])
    fiat_after = next(item for item in accounts if item["id"] == fiat["id"])
    assert wallet_after["balance_base"] == 50000
    assert fiat_after["balance_base"] == -50500

    # Zweiter Import derselben Trades -> Duplikate (strong fingerprint über bank_reference).
    second_batch = client.post(
        f"{PREFIX}/crypto-bridge/trade-imports",
        headers=owner_headers,
        json={
            "wallet_account_id": wallet["id"], "fiat_account_id": fiat["id"],
            "fee_category_id": category["id"], "since": None,
        },
    ).json()
    assert all(row["status"] == "duplicate" for row in second_batch["rows"])

    # reverse_batch storniert die Transferzeilen korrekt (Konten wieder auf 0).
    reversed_batch = client.post(
        f"{PREFIX}/imports/{batch['id']}/reverse",
        headers=owner_headers,
        json={"revision": completed_body["revision"]},
    )
    assert reversed_batch.status_code == 200, reversed_batch.text
    accounts_after_reverse = client.get(f"{PREFIX}/accounts", headers=owner_headers).json()
    wallet_final = next(item for item in accounts_after_reverse if item["id"] == wallet["id"])
    fiat_final = next(item for item in accounts_after_reverse if item["id"] == fiat["id"])
    assert wallet_final["balance_base"] == 0
    assert fiat_final["balance_base"] == 0


def test_trade_import_rejects_non_linked_wallet(client, owner_headers, monkeypatch):
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    _create_household(client, owner_headers)
    wallet = _wallet_account(client, owner_headers)  # NICHT verknüpft
    fiat = _create_account(client, owner_headers, opening_balance=0)

    response = client.post(
        f"{PREFIX}/crypto-bridge/trade-imports",
        headers=owner_headers,
        json={"wallet_account_id": wallet["id"], "fiat_account_id": fiat["id"], "since": None},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "crypto_wallet_not_linked"


def test_trade_import_rejects_wallet_as_fiat_account(client, owner_headers, monkeypatch):
    port = FakePort()
    port.portfolios["owner"] = [{"id": "default", "label": "Portfolio", "currency": "EUR"}]
    _install_fake_port(monkeypatch, port)
    wallet, _fiat = _setup_linked_wallet_and_fiat(client, owner_headers, port)
    other_wallet = _wallet_account(client, owner_headers, name="Zweites Wallet")

    response = client.post(
        f"{PREFIX}/crypto-bridge/trade-imports",
        headers=owner_headers,
        json={"wallet_account_id": wallet["id"], "fiat_account_id": other_wallet["id"], "since": None},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "crypto_fiat_account_invalid"


# ---------------------------------------------------------------------------
# Migration 010
# ---------------------------------------------------------------------------


def test_migration_010_preserves_existing_rows_and_extends_check():
    import sqlite3
    from pathlib import Path

    migrations_dir = Path(__file__).parents[1] / "migrations"
    names = [
        "001_household_core.sql", "002_bank_import.sql", "003_auto_categorize.sql",
        "004_loyalty_foundation.sql", "005_lidl_receipts.sql", "006_optional_gtin.sql",
        "007_payback_browser_bridge.sql", "008_remove_payback_browser_bridge.sql",
        "009_import_formats.sql",
    ]
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    for name in names:
        conn.executescript((migrations_dir / name).read_text())

    conn.execute(
        "INSERT INTO module_haushaltsbuch_households"
        "(id,name,base_currency,timezone,owner_user_id) VALUES(1,'T','EUR','UTC','u1')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_accounts(id,household_id,name,type,currency) "
        "VALUES(1,1,'Wallet','wallet','EUR')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_accounts(id,household_id,name,type,currency) "
        "VALUES(2,1,'Giro','checking','EUR')"
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_batches"
        "(id,household_id,account_id,display_filename,source_format,file_hash,created_by) "
        "VALUES(1,1,2,'bestand.csv','csv',?,'u1')",
        ("0" * 64,),
    )
    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_rows"
        "(id,household_id,batch_id,source_line,fingerprint,fingerprint_strength) "
        "VALUES(1,1,1,1,?,'weak')",
        ("1" * 64,),
    )
    conn.commit()

    conn.executescript((migrations_dir / "010_crypto_bridge.sql").read_text())

    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute(
        "SELECT id,batch_id FROM module_haushaltsbuch_import_rows"
    ).fetchall() == [(1, 1)]
    assert conn.execute(
        "SELECT id,source_format FROM module_haushaltsbuch_import_batches"
    ).fetchall() == [(1, "csv")]

    conn.execute(
        "INSERT INTO module_haushaltsbuch_import_batches"
        "(household_id,account_id,display_filename,source_format,file_hash,created_by) "
        "VALUES(1,2,'cb.json','crypto_trades',?,'u1')",
        ("2" * 64,),
    )
    try:
        conn.execute(
            "INSERT INTO module_haushaltsbuch_import_batches"
            "(household_id,account_id,display_filename,source_format,file_hash,created_by) "
            "VALUES(1,2,'x.xyz','unknown',?,'u1')",
            ("3" * 64,),
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("source_format='unknown' sollte abgelehnt werden")

    conn.execute(
        "UPDATE module_haushaltsbuch_accounts SET linked_portfolio_id='default',"
        "linked_user_id='u1',linked_at='2026-01-01' WHERE id=1"
    )
    try:
        conn.execute(
            "INSERT INTO module_haushaltsbuch_accounts"
            "(household_id,name,type,currency,linked_portfolio_id,linked_user_id,linked_at) "
            "VALUES(1,'Wallet2','wallet','EUR','default','u1','2026-01-02')"
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("ein Portfolio darf nicht an zwei Konten verknüpft sein")

    conn.execute(
        "INSERT INTO module_haushaltsbuch_crypto_snapshots"
        "(account_id,household_id,value_minor,complete,as_of) VALUES(1,1,10000,1,'2026-01-01T00:00:00Z')"
    )
    conn.execute("DELETE FROM module_haushaltsbuch_accounts WHERE id=1")
    assert conn.execute(
        "SELECT * FROM module_haushaltsbuch_crypto_snapshots"
    ).fetchall() == []
