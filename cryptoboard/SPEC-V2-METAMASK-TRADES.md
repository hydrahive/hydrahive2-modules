# Cryptoboard Etappe 2 — MetaMask-Connect und On-Chain-Trade-Historie

## Was

Cryptoboard liest heute Adressen nur manuell eingetragen (`AddressForm.tsx`,
Chains `base`/`ethereum`/`tron`/`bitcoin`) und zeigt davon nur den aktuellen
**Bestand**, nicht den Verlauf. Diese Etappe ergänzt zwei Bausteine:

1. **"Mit MetaMask verbinden"**-Button: statt die Adresse abzutippen, liefert
   die Browser-Extension sie über den injizierten `window.ethereum`-Provider
   (EIP-1193/EIP-6963). Ergebnis ist exakt dieselbe öffentliche Adresse wie
   beim manuellen Eintrag — nur komfortabler und ohne Tippfehlerrisiko.
2. **On-Chain-Trade-Historie**: Swaps, die eine verknüpfte Adresse auf
   unterstützten EVM-Chains (Base/Ethereum, später erweiterbar) getätigt hat,
   werden aus Block-Explorer-Daten rekonstruiert und als Vorschlag in das
   bestehende FIFO-Ledger (`portfolio_store.add`, Arten `buy`/`sell`) überführt
   — über denselben Preview/Commit-Vertrag wie der bestehende CSV-Import
   (`import_routes.py`).

## Warum

- Adresse abtippen ist fehleranfällig (40 Hex-Zeichen) und für Wallet-Besitzer
  unnötig umständlich, wenn die Extension die Adresse schon kennt.
- Der aktuelle Bestand allein verrät nichts über Einstandspreise/realisierten
  Gewinn. Ohne Trade-Historie bleibt die FIFO-Engine für On-Chain-Wallets
  ungenutzt — Nutzer müssten jeden Swap händisch im CSV-Import nachtragen.
- Beides lässt sich **ohne** Private Key, **ohne** Signatur und **ohne**
  Transaktionsfreigabe umsetzen — identische Sicherheitsgarantie wie der
  Rest des Moduls ("NUR Lesen", siehe `chain_clients.py`-Kopfkommentar).

## Verbindliche Produktentscheidungen

### MetaMask-Connect

- Ausschließlich `eth_requestAccounts` (liefert die vom Nutzer in der
  Extension selbst bestätigte Adresse zurück). Keine Signatur-Anfrage, keine
  Transaktion, kein `eth_sendTransaction`, kein `personal_sign` in der
  Basisversion.
- Erkennung über EIP-6963 (`window.addEventListener("eip6963:announceProvider")`),
  damit auch andere injizierte Wallets (Rabby, Coinbase Wallet) denselben
  Button nutzen können, statt MetaMask hart zu verdrahten. Fällt keine
  Extension zurück auf `window.ethereum`, erscheint ein Hinweis statt eines
  Fehlers.
- Das Ergebnis der Verbindung ist **nur die Adresse** — sie durchläuft exakt
  denselben Pfad wie eine manuell eingetragene Adresse (`address_validators.py`,
  `module_cryptoboard_addresses`). Keine Sonderbehandlung, kein separates
  Datenmodell.
- Optional, nicht Teil des Basis-Scopes: Sign-In-with-Ethereum (SIWE) als
  spätere Härtung, falls Adress-Besitz beweisbar sein soll. Für ein reines
  Watch-only-Wallet ohne Freischaltung von irgendetwas ist das nicht
  notwendig und wird daher zurückgestellt (vermeidet unnötige
  Signatur-Prompts).
- Chain-Wechsel in der Extension wird erkannt (`chainChanged`-Event) und bietet
  an, die neue Chain als zusätzliche Adresse hinzuzufügen, statt sie
  automatisch zu übernehmen (Nutzer bestätigt explizit pro Chain).

### On-Chain-Trade-Historie

#### Datenquelle: Alchemy

- **Entscheidung (Till, 2026-11-19):** Datenquelle ist **Alchemy**
  (`alchemy_getAssetTransfers`) über den eigenen, kostenlosen Alchemy-Key
  des jeweiligen Nutzers — kein gemeinsamer Server-Key, kein Fallback auf
  einen anderen Explorer. Begründung: die zuvor geprüften keylosen
  Alternativen für Base sind tot oder unzureichend (Blockscout 403,
  Routescan ohne Unterstützung, Etherscan Base nur im Paid-Plan).
- Der Alchemy-Key wird **pro Nutzer** im Credential-Vault gespeichert
  (`hydrahive.credentials.store`, Name `cryptoboard-alchemy`, Typ `bearer`,
  `url_pattern = "https://*.g.alchemy.com/*"`). Es gibt keinen Server-weiten
  Key und keinen Fallback ohne Key — ohne gespeicherten, geprüften Key liefert
  der On-Chain-Import `alchemy_key_missing`.
- **Kill-Switch:** `HH_CRYPTOBOARD_ONCHAIN_ENABLED` (Konvention wie
  `HH_HAUSHALTSBUCH_LIDL_ENABLED`, Default **an**, `0`/`false`/`no`/`off`
  schaltet den gesamten On-Chain-Trade-Import ab — unabhängig vom
  gespeicherten Key). Geprüft in `onchain_routes.py`, bevor ein
  Alchemy-Call ausgelöst wird.
- **Grenzen pro Lauf:** maximal **1.000 Transaktionen** (eindeutige
  Tx-Hashes) ODER **2 Jahre** zurück, je nachdem was zuerst erreicht wird.
  Ältere Historie wird **nicht** in diesem Lauf geholt — ein Folgelauf mit
  explizitem "weiter zurück"-Parameter (`toBlock` auf den zuletzt erreichten
  Block) holt die nächste Tranche. Das Ergebnis jedes Laufs trägt ein
  Fortsetzungs-Merkmal (`truncated: bool`, `before_block: int | None`),
  damit das Frontend "weitere Historie laden" anbieten kann.
- **Kurse:** CoinGecko liefert im kostenlosen Plan nur **365 Tage**
  historische Kurse. Trades, die älter sind, werden trotzdem importiert,
  aber ohne automatisch aufgelösten Preis — Kennzeichnung `preis_fehlt:
  true`, der Nutzer trägt den Preis im Preview-Schritt händisch nach (wie
  beim CSV-Import mit unauflösbarem Symbol). Das betrifft ausschließlich die
  **Preis**-Auflösung, nicht die Transaktionsgrenze von 2 Jahren oben.

#### Swap-Erkennung: Token-Bewegungen statt Router-Signaturen

- **Entscheidung (Till, 2026-11-19):** Swaps werden **nicht** über bekannte
  DEX-Router-/Methodensignaturen erkannt (ein `dex_signatures.py` mit einer
  Registry bekannter Router entfällt vollständig). Begründung: eine
  Signaturliste deckt immer nur die Router ab, die man kennt, und veraltet
  mit jedem neuen Aggregator/Router.
- Stattdessen: **Swap-Erkennung über die tatsächlichen Token-Bewegungen**
  einer Transaktion, unabhängig davon, welcher Vertrag sie ausgelöst hat.
  Regel: Alle Transfers (`external`, `internal`, `erc20`) einer Transaktion
  werden nach Tx-Hash gruppiert; je Asset wird die Netto-Bewegung relativ zur
  betrachteten Adresse gebildet (negativ = Adresse ist `from`, positiv =
  Adresse ist `to`). Ist **genau ein** Asset netto negativ und **genau ein
  anderes** Asset netto positiv, ist das ein Swap (`sell(A)` + `buy(B)`).
  Jede andere Konstellation (nur eine Richtung, mehrere Assets je Seite,
  Approve ohne Transfer) wird **nicht geraten**, sondern als "unklare
  Transaktion" mit den Rohdaten (Hash, Zeit, beteiligte Token/Mengen,
  Richtung) im Preview gezeigt.
- **Sonderfall Wrap/Unwrap (WETH↔ETH):** Eine Transaktion, die ausschließlich
  natives ETH gegen WETH des bekannten Vertrags tauscht (Base
  `0x4200000000000000000000000000000000000006`, Ethereum
  `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`), ist **kein Trade** (kein
  Kursereignis) und wird als eigener Hinweistyp ausgegeben, nicht als
  `buy`/`sell`.
- Mengen werden ausschließlich aus `rawContract.value` (Hex) und
  `rawContract.decimal`/`decimals` als Integer-Basiseinheiten bzw. `Decimal`
  berechnet — **nicht** aus dem von Alchemy mitgelieferten gerundeten
  Float-Feld `value` (das rundet bei hoher Dezimalstellenzahl/großen Beträgen
  falsch).
- Jede erkannte Swap-Transaktion wird in das bestehende Zwischenformat des
  CSV-Importers übersetzt (`coin_id`, `symbol`, `kind`, `quantity`, `price`,
  `fee`, `executed_at`, `hash`) und läuft durch **denselben**
  Preview/Commit-Vertrag wie der manuelle CSV-Import — keine neue,
  parallele Ledger-Schreibroute.
- Fingerprint/Dedup: `import_hash` = `{chain}:{txhash}:sell` bzw. `:buy`
  (je Swap zwei Ledger-Einträge), Dedup über vorhandene Hashes wie beim CSV-Import.
- Endpunkte: `POST /portfolio/import/onchain/preview` `{address_id, to_block?}`
  → `transactions` (sell+buy je Swap, Zahlen als exakte Strings, Flags
  `resolved`/`preis_fehlt`/`gebuehr_fehlt`/`duplicate`), `wraps`, `unklar`,
  `truncated`, `before_block`, `counts`; `POST /portfolio/import/onchain/commit`
  `{transactions}` → `{imported, skipped, skipped_details}`. Einträge ohne Preis
  oder coin_id werden nicht gebucht.
- Der Alchemy-Key steht nie in einer URL: er geht nur im Header
  `Authorization: Bearer <key>`.
- Gas-Fee der Transaktion wird als anteilige Fee in EUR zum Ausführungszeitpunkt
  umgerechnet und in die FIFO-Kostenbasis eingerechnet (`fifo.py`-Vertrag:
  Fee verteuert den Einstand).
- Nur Lesen bleibt absolute Grenze: Kein Provider-Call, der eine Transaktion
  signiert oder sendet; der Alchemy-Client akzeptiert nur eine feste
  Allowlist lesender Methoden (`alchemy_getAssetTransfers`,
  `eth_getTransactionReceipt`, `eth_blockNumber`, `eth_getTransactionByHash`)
  — jede andere Methode wird vor dem Netzaufruf abgelehnt. Der gesamte
  Baustein bleibt im bestehenden "NUR Lesen"-Vertrag des Moduls.

## Nicht-Ziele dieser Etappe

- Kein automatischer, ungeprüfter Import — jede erkannte Transaktion läuft
  durch das Preview/Commit-Muster, genau wie CSV-Importe heute.
- Keine Transaktionssignatur, kein Senden von Transaktionen, kein
  `eth_sendTransaction` in dieser Etappe.
- Keine Abdeckung aller DEX-Protokolle von Tag 1 — Start mit den größten
  Uniswap-kompatiblen Routern auf Base/Ethereum, Erweiterung folgt inkrementell
  nach demselben `_EVM`-Dict-Muster wie bestehende Token.
- Keine NFT-Trades in dieser Etappe.

## Abgrenzung zur bestehenden Funktionalität

- `backend/chain_clients.py` liefert weiterhin nur den **aktuellen Bestand**.
  Die Trade-Historie ist ein eigener, neuer Modulteil mit eigenem
  Zeithorizont (Transaktionsliste statt Momentaufnahme).
- `backend/import_routes.py`/`csv_import.py` bleiben unverändert als Pfad für
  Exchange-Exports (Kraken, Binance etc.); On-Chain-Trades bekommen einen
  eigenen Preview/Commit-Endpunkt mit identischem Vertrag, aber eigener
  Datenquelle (Chain statt Datei).
