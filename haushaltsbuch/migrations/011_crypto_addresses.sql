-- Etappe A1/A2 (VERTRAG-PORT-V2.md): Konto <-> Cryptoboard-Adressen (Read-Port
-- v2), zusaetzlich zur bestehenden Portfolio-Verknuepfung (v1, 010). Ein
-- Wallet-Konto kann an eine oder mehrere Adressen DESSELBEN Users gebunden
-- sein (z.B. Base + Ethereum = dieselbe 0x-Adresse, ein Konto); eine Adresse
-- darf aber hoechstens an einem Konto haengen (UNIQUE je Haushalt+User).
--
-- Lose Modulreferenz wie bei linked_portfolio_id in 010: address_id ist die
-- ID aus module_cryptoboard_addresses (anderes Modul), kein FK darauf - der
-- Read-Port prueft Existenz/Ownership, nicht ein Fremdschluessel hier.
--
-- ON DELETE CASCADE vom Konto: wird das Wallet-Konto geloescht, verschwinden
-- auch seine Adress-Verknuepfungen (keine verwaisten Zeilen).
CREATE TABLE IF NOT EXISTS module_haushaltsbuch_account_crypto_addresses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_accounts(id) ON DELETE CASCADE,
  household_id INTEGER NOT NULL REFERENCES module_haushaltsbuch_households(id) ON DELETE CASCADE,
  linked_user_id TEXT NOT NULL,
  address_id INTEGER NOT NULL,
  chain TEXT NOT NULL,
  address TEXT NOT NULL,
  linked_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(household_id, linked_user_id, address_id)
);

CREATE INDEX IF NOT EXISTS idx_hh_account_crypto_addresses_account
  ON module_haushaltsbuch_account_crypto_addresses(account_id);

-- Letzter bekannter Bestand (Holdings) je Konto, fuer den Snapshot-Rueckfall
-- wenn der Port v2 / die Kursquelle nicht verfuegbar ist - analog zu
-- module_haushaltsbuch_crypto_snapshots (010), aber zusaetzlich mit den
-- einzelnen Coin-Positionen (holdings_json) statt nur dem Gesamtwert.
CREATE TABLE IF NOT EXISTS module_haushaltsbuch_crypto_holdings_snapshots (
  account_id INTEGER PRIMARY KEY REFERENCES module_haushaltsbuch_accounts(id) ON DELETE CASCADE,
  household_id INTEGER NOT NULL,
  value_minor INTEGER NOT NULL,
  complete INTEGER NOT NULL DEFAULT 1 CHECK(complete IN (0,1)),
  as_of TEXT NOT NULL,
  holdings_json TEXT NOT NULL,
  addresses_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hh_crypto_holdings_snapshots_household
  ON module_haushaltsbuch_crypto_holdings_snapshots(household_id);
