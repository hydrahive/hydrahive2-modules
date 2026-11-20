# PLAN V2 — MetaMask-Connect und On-Chain-Trade-Historie

Grundlage: `SPEC-V2-METAMASK-TRADES.md`
Scope: Wallet-Connect-Button (EIP-1193/EIP-6963), On-Chain-Swap-Erkennung für
EVM-Chains, Übersetzung in den bestehenden Import-Preview/Commit-Vertrag.
Kein Signieren, kein Senden von Transaktionen.

## Ziel

Adressen lassen sich per Klick statt Abtippen hinzufügen, und Swaps einer
verknüpften Adresse lassen sich als FIFO-Ledger-Einträge importieren — über
denselben geprüften Preview/Commit-Pfad wie der bestehende CSV-Import. Jede
Phase ist separat testbar und commitbar.

## Geplante Dateien

### Backend — On-Chain-Trade-Historie

Datenquelle Alchemy (Till, 2026-11-19), Swap-Erkennung über Token-Bewegungen
statt Router-Signaturen — **`dex_signatures.py` entfällt vollständig**
(siehe SPEC, Abschnitt "Swap-Erkennung").

- `backend/alchemy_key.py` — Key-Verwaltung pro Nutzer (Speichern mit
  Vorab-Test, maskierter Status, Löschen) über
  `hydrahive.credentials.store`, Credential-Name `cryptoboard-alchemy`
- `backend/alchemy_key_routes.py` — Routen für die Key-Verwaltung
  (PUT/POST/GET/DELETE), eingehängt wie `wallet_routes.py`/`import_routes.py`
- `backend/alchemy_client.py` — Netz-Client gegen
  `https://{chain}-mainnet.g.alchemy.com/v2` mit Key NUR im Header
  `Authorization: Bearer <key>` (nie in der URL → nie in httpx-Logs/Exceptions),
  Methoden-Allowlist (nur
  lesend), Kill-Switch, `fetch_transfers()` mit Paging/Grenzen laut SPEC
- `backend/onchain_swaps.py` — reine Funktionen: Transfers nach Tx-Hash
  gruppieren, Netto-Bewegung je Asset, Swap-Regel, Wrap/Unwrap-Sonderfall,
  unklare Transaktionen als Rohdaten-Liste. Kein Netzzugriff, keine
  Preisauflösung (Teil B).
- `backend/onchain_resolve.py` / `backend/onchain_gas.py` — coin_id-Auflösung,
  EUR-Tageskurs (Stable > ETH/WETH > sonst), Gas nur als Absender (+ l1Fee Base)
- `backend/onchain_import.py` — Preview-Aufbau und Commit-Logik (Decimal intern,
  EINE float-Grenze direkt vor `store.add`)
- `backend/onchain_import_routes.py` — `POST /portfolio/import/onchain/preview`
  `{address_id, to_block?}` und `POST /portfolio/import/onchain/commit`
  `{transactions:[…]}`, gleicher Vertrag wie `import_routes.py`

### Migrationen

- **Keine.** `004_import_hash.sql` (nicht-eindeutiger Index `user, import_hash`)
  reicht; Dedup wie beim CSV-Import über `existing_hashes` + innerhalb des
  Requests. Ein UNIQUE-Index wäre auf Bestandsdaten nicht sicher anlegbar.
  Restrisiko: zwei exakt gleichzeitige Commits desselben Nutzers.

### Frontend — MetaMask-Connect

- `frontend/components/WalletConnectButton.tsx` — EIP-6963-Discovery,
  `eth_requestAccounts`, liefert Adresse an den bestehenden
  `cryptoApi.addWallet`-Aufruf; Fallback-Hinweis ohne erkannte Extension
- Erweiterung `frontend/components/AddressForm.tsx` — Connect-Button neben
  dem manuellen Adressfeld, beide Wege führen zum selben `addWallet`-Call
- Erweiterung `frontend/types.ts` — Typen für EIP-6963-Provider-Infos

### Frontend — On-Chain-Trade-Import

- `frontend/components/OnchainTradeImportDialog.tsx` — Vorschau/Commit im
  Stil des bestehenden CSV-Import-Dialogs, inkl. sichtbarer Liste
  "unbekannte Transaktion" für nicht erkannte Vertragsinteraktionen
- Erweiterung `frontend/views/WalletsView.tsx` — Aktion "Trades dieser
  Adresse importieren" je verknüpfter EVM-Adresse
- Erweiterung `frontend/api.ts` — Aufrufe für die neuen Onchain-Import-Routen

### Tests

- `tests/test_alchemy_key.py` *(Teil A)* — Key setzen mit Vorab-Test (Erfolg,
  401/403, Netzfehler), bei Fehler wird nichts gespeichert; Status nur
  maskiert; Löschen; Key nie im Klartext in Fehlertexten/Logs
- `tests/test_alchemy_client.py` *(Teil A)* — Methoden-Allowlist lehnt
  schreibende Methoden ab (`eth_sendRawTransaction`, `eth_sendTransaction`,
  `personal_sign`), Kill-Switch, Paging über `pageKey`, beide Grenzen
  (1.000 Tx / 2 Jahre), Fortsetzungs-Merkmal
- `tests/test_onchain_swaps.py` *(Teil A)* — Swap-Regel (genau 1 raus + genau
  1 rein), Mehrdeutigkeit → "unklar", Wrap/Unwrap-Sonderfall, exaktes
  Mengen-Parsing aus `rawContract.value`/`decimal` (Gegenbeispiel: Float-Feld
  würde falsch runden)
- `tests/test_onchain_import_routes.py` *(Teil B)* — Preview/Commit-Vertrag,
  Preisauflösung inkl. `preis_fehlt` bei >365 Tagen, Gas-Fee-Umlage, Dedup
  über Transaktionshash
- Frontend: Test für `WalletConnectButton` mit gemocktem `window.ethereum`
  (kein echter Extension-Zugriff im Testlauf)

## Implementierungsreihenfolge

### Phase 0 — Vorprüfung

#### Task 0.1 — Explorer-API-Auswahl je Chain

Festlegen, welche keylose (oder mit optionalem Key als Fallback) Quelle pro
Chain Transaktionslisten liefert (z. B. publicnode RPC + `eth_getLogs` auf
bekannte Router-Adressen für Base/Ethereum). Rate-Limits und Pagination-
Verhalten dokumentieren, bevor Code entsteht.

#### Task 0.2 — entfällt (Router-Signatur-Liste)

Entfällt vollständig: Swap-Erkennung läuft über Token-Bewegungen je
Transaktion (siehe SPEC), nicht über eine Liste bekannter Router-Signaturen.
Kein `dex_signatures.py`.

### Phase 1 — MetaMask-Connect (unabhängig von Phase 2)

#### Task 1.1 — WalletConnectButton

`WalletConnectButton.tsx`, EIP-6963-Discovery, `eth_requestAccounts`,
Einbindung in `AddressForm.tsx`.

#### Task 1.2 — Tests Phase 1

Frontend-Test mit gemocktem Provider; manueller Test-Durchlauf mit echter
MetaMask-Extension vor Merge (Dokumentation im PR, kein automatisierter
Extension-Test nötig).

### Phase 2 — On-Chain-Trade-Historie

Umgesetzt in zwei Etappen (TEIL A, TEIL B), siehe Auftragsbeschreibung
"Cryptoboard Etappe 2, Phase 2a". Reihenfolge bewusst Backend-first, ohne
Router-Signatur-Vorprüfung (entfällt, siehe oben).

#### TEIL A — Key-Verwaltung, Alchemy-Client, Swap-Erkennung (reine Funktionen)

- **Task A2** — `alchemy_key.py` + `alchemy_key_routes.py`: Key setzen
  (Vorab-Test VOR dem Speichern, klare Fehlercodes für ungültig/Base nicht
  freigegeben/Netzfehler), Status nur maskiert, Löschen. Key nie loggen, nie
  in Fehlertexten (auch nicht über die URL in `raise_for_status`-Fehlern).
- **Task A3** — `alchemy_client.py`: Netz-Call gekapselt (Muster
  `chain_clients._rpc`), Methoden-Allowlist, Kill-Switch,
  `fetch_transfers(chain, address, ...)` mit Paging (`pageKey`) und beiden
  Grenzen (1.000 Tx / 2 Jahre), Fortsetzungs-Merkmal für Folgeläufe.
- **Task A4** — `onchain_swaps.py`: reine Funktionen, Gruppierung nach
  Tx-Hash, Netto-Bewegungs-Regel, Wrap/Unwrap-Sonderfall, "unklar"-Liste,
  exaktes Mengen-Parsing (Integer-Basiseinheiten/Decimal, nicht das
  Float-Feld). Noch ohne Preis-/coin_id-Auflösung — die liefert Teil B.

#### TEIL B — Preise, Gas, Preview/Commit, Migration (falls nötig)

- **Preisauflösung**: coin_id-Zuordnung der erkannten Token (Kontraktadresse
  → bekannte `_EVM`-Token-Liste bzw. CoinGecko-Suche wie beim CSV-Import),
  CoinGecko-Historienpreis zum Ausführungszeitpunkt; Trades älter als 365
  Tage bekommen `preis_fehlt: true` statt eines automatischen Preises
  (CoinGecko-Free-Grenze).
- **Gas-Fee-Umlage**: Transaktionsgebühr (aus `eth_getTransactionReceipt`,
  `gasUsed * effectiveGasPrice`) in EUR zum Ausführungszeitpunkt umgerechnet,
  als anteilige Fee in die FIFO-Kostenbasis eingerechnet (`fifo.py`-Vertrag).
- **Preview/Commit-Endpunkte**: `onchain_import_routes.py`
  (`/portfolio/import/onchain/preview`, `.../commit`), Wiederverwendung des
  bestehenden Commit-Musters aus `import_routes.py` (Dedup über
  `import_hash`, `store.add`). Hier passiert die EINE Umwandlung von
  Decimal/Integer-Basiseinheiten (Teil A) ins Ledger-Format
  (REAL/float wie `migrations/002_portfolio.sql`, `portfolio_store.add`).
- **Migration**: geprüft → keine (siehe „Migrationen“).
- **Stand 20.11.2026**: umgesetzt. `import_hash` = `{chain}:{txhash}:sell|buy`;
  Flags je Eintrag `resolved`, `preis_fehlt`, `gebuehr_fehlt`, `duplicate`;
  Commit überspringt mit Grund (`duplikat`, `preis_fehlt`, `coin_id_fehlt`,
  `hash_ungueltig`, `zeit_ungueltig`, `ledger_full`); fee null → 0.
- **Frontend-Import-Dialog**: `OnchainTradeImportDialog.tsx`, Einbindung in
  `WalletsView.tsx` (eigener, paralleler Auftrag
  `cryptoboard-metamask-plan`/`cb-metamask-frontend`).
- **Tests**: `test_onchain_import_routes.py` (Preview/Commit-Vertrag,
  `preis_fehlt`, Gas-Fee-Umlage, Dedup).

### Phase 3 — Abschluss

#### Task 3.1 — Dokumentation und Modulversion

`manifest.json` Version anheben, Nutzungshinweis ("nur Lesen, keine
Transaktionssignatur") sichtbar in der UI verankern (analog zum bestehenden
`wl_disclaimer`-Text).

#### Task 3.2 — Vollständiger Testlauf

`pytest` über das gesamte Modul; Fokus auf Dedup-Korrektheit (kein Trade wird
doppelt gebucht, egal ob zuerst per CSV oder per On-Chain-Import eingespielt).

## Abhängigkeiten zwischen Phasen

- Phase 1 (MetaMask-Connect) ist unabhängig von Phase 2 und kann sofort
  begonnen werden.
- Phase 2 setzt Task 0.1/0.2 voraus (Datenquelle und erste Signaturliste
  geklärt), sonst entsteht Rate ein Rateversuch statt einer belastbaren
  Erkennung.
- Phase 2 ist unabhängig von Phase 1 nutzbar: Trade-Import funktioniert auch
  für manuell eingetragene Adressen, MetaMask-Connect ist nur der komfortable
  Zugangsweg für die Adresse selbst.
