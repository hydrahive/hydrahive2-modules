# PLAN V9 — Auswertungen, erweiterte Importe, Crypto-Brücke

Grundlage: `SPEC-V9-AUSWERTUNGEN-CRYPTO.md`
Scope: serverseitig vorberechnete Diagramm-Daten, PDF-/PayPal-Import,
read-only Brücke zu `cryptoboard`. Keine FinTS-Anbindung, kein Bild-OCR.

## Ziel

Die Roadmap-Etappe 9 ("Auswertungen und Exporte") wird fachlich konkretisiert
und umgesetzt, gleichzeitig wird die bisher isolierte Krypto-Vermögensbildung
an `cryptoboard` angebunden. Jede Phase ist separat testbar und commitbar.
Kein Live-Zugriff auf Cryptoboard-Daten vor abgeschlossenem Berechtigungs-
Review (Phase 2).

## Geplante Dateien

### Backend — Auswertungen

- `backend/reports.py` — Aggregationslogik (Cashflow, Vermögensverlauf,
  Kategorieverteilung, Budget-Verlauf, Fixkosten-Anteil), reine Lesefunktionen
  auf Ledger/Budgets/Assets, Integer-Arithmetik durchgehend
- `backend/routes_reports.py` — `/reports/*`-Endpunkte inkl. CSV-Export
  desselben Aggregats

### Backend — Import-Erweiterung

- `backend/import_pdf.py` — Textschicht-Extraktion von Bank-PDF-Kontoauszügen,
  Ablehnung von Scan-PDFs ohne Textschicht mit eindeutigem Fehlercode
- `backend/import_paypal.py` — PayPal-CSV-Profil, Gebühren-Split, Verwerfen
  von Währungsumrechnungszeilen
- Erweiterung `backend/import_parsers.py` — `ImportFormat` um `"pdf"` ergänzen,
  Dispatch in `parse_import`
- Erweiterung `backend/import_models.py` — Profilvariante `paypal` in den
  bestehenden CSV-Mapping-Typen

### Backend — Crypto-Brücke

- `backend/crypto_bridge.py` — liest Portfolio-Bestand/-Wert über die
  modulinterne Schnittstelle von `cryptoboard`, keine eigene Kurslogik,
  klar abgegrenzte Fehlerklasse bei fehlendem/deaktiviertem Modul
- `backend/crypto_bridge_models.py` — Pydantic-DTOs für Verknüpfung und
  Trade-Import-Vorschau
- Erweiterung `backend/models.py` — `linked_portfolio_id` auf `AccountUpdate`
  (nullable, nur für `type == "wallet"`)
- Erweiterung `backend/assets.py` — Verknüpfen/Trennen, Sperre manueller
  Saldobuchungen bei aktiver Verknüpfung, Rückfall auf letzten Saldo
- `backend/routes_crypto_bridge.py` — Verknüpfungs- und Trade-Import-Endpunkte

### Migrationen

- `migrations/XXX_crypto_bridge.sql` — Spalte `linked_portfolio_id` auf
  Konten-Tabelle, Index, Fremdschlüssel-Referenz als lose Modul-Referenz
  (kein Hard-FK über Modulgrenzen, Konsistenz über Anwendungscode)

### Frontend

- `frontend/ReportsView.tsx` — neue Auswertungsseite mit Zeitraumwahl,
  fünf Diagrammen (recharts, analog `cryptoboard/frontend/components/
  ValueChart.tsx`/`PriceChart.tsx` als Stilvorlage) plus Tabellenansicht
  und CSV-Export-Button je Diagramm
- Erweiterung `frontend/DashboardView.tsx` — Cashflow-Mini-Chart und
  Vermögensverlauf-Mini-Chart ergänzen bestehende Kacheln, Link zur
  vollständigen `ReportsView`
- `frontend/CryptoLinkDialog.tsx` — Wallet-Konto mit Cryptoboard-Portfolio
  verknüpfen/trennen, Hinweis bei fehlendem Modul
- `frontend/CryptoTradeImportDialog.tsx` — Trade-Import-Vorschau im
  bestehenden Import-Prüfbereich-Stil (wiederverwendet `ImportBatchView.tsx`-
  Muster)
- Erweiterung `frontend/ImportUploadDialog.tsx` — Formatwahl `pdf`/`paypal`
- Erweiterung `frontend/types.ts` — `linked_portfolio_id`, Report-DTOs
- Erweiterung `frontend/api.ts` — Report- und Crypto-Bridge-Aufrufe
- Erweiterung `frontend/HaushaltsbuchPage.tsx` — Navigationseintrag
  "Auswertungen"

### Tests

- `tests/test_reports.py` — Aggregation, Integer-Treue, Zeitraumgrenzen
- `tests/test_import_pdf.py` — Textschicht-Erkennung, Scan-Ablehnung
- `tests/test_import_paypal.py` — Gebühren-Split, FX-Zeilen-Verwurf
- `tests/test_crypto_bridge.py` — Verknüpfung, Sperre manueller Buchungen,
  Rückfallverhalten bei deaktiviertem Modul, Berechtigungsgrenze zwischen
  Haushaltsmitgliedern
- `tests/test_crypto_bridge_permissions.py` — eigener Test für die
  Berechtigungsgrenze aus der Spec (kein Zugriff auf fremde Portfolios ohne
  explizite Cryptoboard-Freigabe)
- `tests/fixtures/reports/` — synthetische Mehrjahres-Ledger-Fixtures für
  Aggregationstests

## Implementierungsreihenfolge

### Phase 0 — Vorprüfung

#### Task 0.1 — Cryptoboard-Schnittstellen-Review

Klären, welche stabile Lese-Schnittstelle `cryptoboard` modulintern bereits
anbietet (`backend/portfolio.py`, `backend/valuation.py`), ob sie für
modulübergreifenden Lesezugriff geeignet ist oder zuerst ein schmaler,
expliziter Read-Port ergänzt werden muss. Kein Code in späteren Phasen vor
diesem Review.

#### Task 0.2 — Roadmap-Eintrag aktualisieren

`ROADMAP.md` Etappe 9 von Stichwortliste auf "siehe SPEC-V9/PLAN-V9"
umstellen, analog zum bestehenden Muster bei Etappe 2/4/6.

### Phase 1 — Auswertungen (unabhängig von Crypto-Brücke)

#### Task 1.1 — Aggregationslogik Backend

`backend/reports.py` mit den fünf in der Spec genannten Aggregaten,
ausschließlich Integer-Arithmetik, Zeitraumparameter, Haushaltsmitgliedschaft
geprüft wie bei bestehenden Endpunkten.

#### Task 1.2 — Report-Endpunkte

`backend/routes_reports.py`, Registrierung in `backend/__init__.py`, CSV-Export
je Aggregat.

#### Task 1.3 — ReportsView Frontend

`frontend/ReportsView.tsx` mit den fünf Diagrammen, Zeitraumwahl,
Tabellenalternative, Navigationseintrag in `HaushaltsbuchPage.tsx`.

#### Task 1.4 — Dashboard-Mini-Charts

Cashflow- und Vermögensverlauf-Mini-Charts in `DashboardView.tsx`, Link zu
`ReportsView`.

#### Task 1.5 — Tests Phase 1

`tests/test_reports.py`, Fixtures unter `tests/fixtures/reports/`.

### Phase 2 — Import-Erweiterung (unabhängig von Phase 1 und 3)

#### Task 2.1 — PDF-Kontoauszug-Parser

`backend/import_pdf.py`, Erweiterung `import_parsers.py`/`import_models.py`,
klare Fehlermeldung und Verweis auf Etappe-4-OCR-Pfad bei Scan-PDFs.

#### Task 2.2 — PayPal-CSV-Profil

`backend/import_paypal.py`, Gebühren-Split, FX-Zeilen-Erkennung.

#### Task 2.3 — Frontend-Formatwahl

Erweiterung `ImportUploadDialog.tsx` um `pdf`/`paypal`.

#### Task 2.4 — Tests Phase 2

`tests/test_import_pdf.py`, `tests/test_import_paypal.py`.

### Phase 3 — Crypto-Brücke (nach bestandenem Task 0.1)

#### Task 3.1 — Read-Port in Cryptoboard (falls laut Task 0.1 nötig)

Schmale, explizite Lese-Schnittstelle in `cryptoboard` ergänzen, falls kein
geeigneter Port existiert. Eigener PR im Modul `cryptoboard`, bevor
Haushaltsbuch darauf zugreift.

#### Task 3.2 — Crypto-Bridge-Backend

`backend/crypto_bridge.py`, `backend/crypto_bridge_models.py`, Erweiterung
`models.py`/`assets.py`, Migration für `linked_portfolio_id`.

#### Task 3.3 — Trade-Import als Importvertrag

`routes_crypto_bridge.py` Trade-Import-Vorschau, Abbildung auf bestehenden
Importvertrag (Transfer + Gebühren-Split), läuft durch denselben
Prüfbereich wie Bank-Importe.

#### Task 3.4 — Frontend Crypto-Bridge

`CryptoLinkDialog.tsx`, `CryptoTradeImportDialog.tsx`, Einbindung in
`AccountsView.tsx`.

#### Task 3.5 — Berechtigungs- und Kill-Switch-Tests

`tests/test_crypto_bridge.py`, `tests/test_crypto_bridge_permissions.py`:
Rückfallverhalten bei deaktiviertem Modul, keine Mitglieder-übergreifende
Portfoliosicht ohne explizite Cryptoboard-Freigabe.

### Phase 4 — Abschluss

#### Task 4.1 — Vermögensverlauf inkl. Crypto

`reports.py`-Vermögensaggregat um verknüpfte Wallet-Live-Werte ergänzen,
sobald Phase 1 und Phase 3 beide stehen.

#### Task 4.2 — Dokumentation

`README.de.md`/`README.md` und `ROADMAP.md` final aktualisieren,
Modulversion anheben (`manifest.json`).

#### Task 4.3 — Vollständiger Testlauf

`pytest` über das gesamte Modul, Fokus auf Ledger-Invarianten
(keine Floats, Integer-Treue) und Berechtigungsgrenzen laut
übergreifenden Leitplanken der `ROADMAP.md`.

## Abhängigkeiten zwischen Phasen

- Phase 1 und Phase 2 sind unabhängig voneinander und von Phase 3 — können
  parallel bearbeitet werden.
- Phase 3 setzt Task 0.1 voraus (Cryptoboard-Schnittstellen-Klärung), sonst
  entsteht eine stillschweigende Abhängigkeit auf interne Cryptoboard-Module,
  die bei einem Cryptoboard-Refactor brechen kann.
- Task 4.1 setzt sowohl Phase 1 (Vermögensaggregat existiert) als auch
  Phase 3 (Live-Wert verknüpfter Wallets existiert) voraus.
