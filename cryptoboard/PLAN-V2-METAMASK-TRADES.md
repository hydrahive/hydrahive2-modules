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

- `backend/onchain_trades.py` — holt Transaktionsliste einer Adresse je
  EVM-Chain, erkennt Swaps über bekannte Router-Signaturen, übersetzt Treffer
  in das bestehende Zwischenformat des CSV-Importers
- `backend/dex_signatures.py` — Registry bekannter DEX-Router-/Methodensignaturen
  (Uniswap V2/V3 zuerst), erweiterbar nach demselben Muster wie `_EVM` in
  `chain_clients.py`
- `backend/onchain_import_routes.py` — `/portfolio/import/onchain/preview` und
  `/portfolio/import/onchain/commit`, gleicher Vertrag wie
  `import_routes.py`, eigene Datenquelle
- Erweiterung `backend/chain_clients.py` — Transaktionslisten-Fetcher ergänzen
  (bestehende `_rpc`/`_get`-Helfer wiederverwenden, Netz-Calls weiterhin
  gekapselt und mockbar)

### Migrationen

- `migrations/007_onchain_import_hash.sql` — eigener Index/Constraint für
  On-Chain-Transaktionshashes als `import_hash`, falls nicht schon durch
  `004_import_hash.sql` abgedeckt (prüfen vor Neuanlage)

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

- `tests/test_dex_signatures.py` — Signaturerkennung, unbekannte Methoden
  bleiben unbekannt statt falsch zugeordnet
- `tests/test_onchain_trades.py` — Übersetzung Chain-Transaktion → Import-
  Zwischenformat, Fee-Umlage, Dedup über Transaktionshash
- `tests/test_onchain_import_routes.py` — Preview/Commit-Vertrag, Rate-Limit-
  Begrenzung (max. Transaktionen pro Lauf)
- Frontend: Test für `WalletConnectButton` mit gemocktem `window.ethereum`
  (kein echter Extension-Zugriff im Testlauf)

## Implementierungsreihenfolge

### Phase 0 — Vorprüfung

#### Task 0.1 — Explorer-API-Auswahl je Chain

Festlegen, welche keylose (oder mit optionalem Key als Fallback) Quelle pro
Chain Transaktionslisten liefert (z. B. publicnode RPC + `eth_getLogs` auf
bekannte Router-Adressen für Base/Ethereum). Rate-Limits und Pagination-
Verhalten dokumentieren, bevor Code entsteht.

#### Task 0.2 — Router-Signatur-Liste Phase 1

Erste, bewusst kleine Liste bekannter Uniswap-V2/V3-Router auf Base und
Ethereum für `dex_signatures.py`. Alles andere bleibt in Phase 1 explizit
"unbekannt", nicht geraten.

### Phase 1 — MetaMask-Connect (unabhängig von Phase 2)

#### Task 1.1 — WalletConnectButton

`WalletConnectButton.tsx`, EIP-6963-Discovery, `eth_requestAccounts`,
Einbindung in `AddressForm.tsx`.

#### Task 1.2 — Tests Phase 1

Frontend-Test mit gemocktem Provider; manueller Test-Durchlauf mit echter
MetaMask-Extension vor Merge (Dokumentation im PR, kein automatisierter
Extension-Test nötig).

### Phase 2 — On-Chain-Trade-Historie (nach Task 0.1/0.2)

#### Task 2.1 — Transaktionslisten-Fetcher

Erweiterung `chain_clients.py` um Transaktionslisten-Abruf je verknüpfter
EVM-Adresse, Zeitraum-/Mengenbegrenzung laut Spec.

#### Task 2.2 — Swap-Erkennung

`dex_signatures.py` + `onchain_trades.py`: bekannte Router-Treffer →
`buy`/`sell`-Zwischenformat; unbekannte Treffer → eigene Liste, kein
automatisches Raten.

#### Task 2.3 — Preview/Commit-Endpunkte

`onchain_import_routes.py`, Wiederverwendung des bestehenden Commit-Musters
aus `import_routes.py` (Dedup über `import_hash`, `store.add`).

#### Task 2.4 — Frontend-Import-Dialog

`OnchainTradeImportDialog.tsx`, Einbindung in `WalletsView.tsx`.

#### Task 2.5 — Tests Phase 2

`test_dex_signatures.py`, `test_onchain_trades.py`,
`test_onchain_import_routes.py`.

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
