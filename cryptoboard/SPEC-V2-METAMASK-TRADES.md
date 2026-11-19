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

- Datenquelle: öffentliche Explorer-/RPC-APIs, analog zum bestehenden
  `chain_clients.py`-Muster (keylos bevorzugt, ein optionaler API-Key pro
  Chain als Fallback für höhere Rate-Limits, niemals Pflicht).
- Erkennung von Swaps über bekannte DEX-Router-/Pool-Signaturen (z. B.
  Uniswap-V2/V3-Router auf Ethereum/Base). Nicht erkannte Vertragsinteraktionen
  werden **nicht** stillschweigend als Trade interpretiert, sondern als
  "unbekannte Transaktion" mit Rohdaten im Preview sichtbar gemacht und
  müssen vom Nutzer bewusst zugeordnet oder verworfen werden.
- Jede erkannte Transaktion wird in das bestehende Zwischenformat des
  CSV-Importers übersetzt (`coin_id`, `symbol`, `kind`, `quantity`, `price`,
  `fee`, `executed_at`, `hash`) und läuft durch **denselben**
  Preview/Commit-Vertrag wie der manuelle CSV-Import — keine neue,
  parallele Ledger-Schreibroute.
- Fingerprint/Dedup: Transaktionshash der Chain ist der stabile `import_hash`
  (stärker als der CSV-Fingerprint, da eindeutig und nicht manipulierbar).
- Gas-Fee der Transaktion wird als anteilige Fee in EUR zum Ausführungszeitpunkt
  umgerechnet und in die FIFO-Kostenbasis eingerechnet (`fifo.py`-Vertrag:
  Fee verteuert den Einstand).
- Zeitraum/Umfang begrenzt (z. B. letzte 1.000 Transaktionen oder 2 Jahre pro
  Lauf), um Explorer-Rate-Limits und Importgröße nicht zu sprengen; weitere
  Läufe holen ältere Historie nach.
- Nur Lesen bleibt absolute Grenze: Kein Provider-Call, der eine Transaktion
  signiert oder sendet. Der gesamte Baustein bleibt im bestehenden
  "NUR Lesen"-Vertrag des Moduls.

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
