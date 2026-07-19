# Plan: PAYBACK Browser-Bridge V1

## Ziel

Ein manueller read-only PAYBACK-Import über eine lokale Chromium-Erweiterung mit sicherem Einmalcode, idempotenter Loyalty-Persistenz und einer Daten-/Analyseansicht im Haushaltsbuch.

## Dateien

- `migrations/007_payback_browser_bridge.sql` – Pairing-Flows und optionale Einkaufsbeträge.
- `backend/payback_bridge_models.py` – strikte Import-/Flow-Schemas und Limits.
- `backend/payback_bridge.py` – Codeerzeugung, Status, Import, Verbindung und Persistenz.
- `backend/payback_data.py` – sichtbarkeitsgeschützte Read-API und Kennzahlen.
- `backend/payback_extension.py` – reproduzierbares ZIP-Paket ohne Dateipfad-Input.
- `backend/routes_loyalty.py`, `backend/loyalty_requests.py` – Endpoints.
- `backend/loyalty_provider.py`, `backend/loyalty_persistence.py`, `backend/loyalty_models.py` – strukturierter Einkaufsbetrag.
- `browser-extension/payback-bridge/*` – Manifest-V3-Popup, Content-Extractor und Styles.
- `frontend/PaybackBridgeDialog.tsx` – Flow, Download, Installations-/Erfassungsschritte und Polling.
- `frontend/PaybackData.tsx` – Punktestand, Kennzahlen, Aktivitäten und Coupons.
- `frontend/LoyaltyView.tsx`, `frontend/LoyaltyConnectionCard.tsx`, `frontend/loyaltyApi.ts`, `frontend/loyaltyTypes.ts` – Integration.
- `tests/test_payback_bridge.py` – Auth, Token-Lebenszyklus, Limits, Idempotenz, Scoping.
- `tests/test_payback_extension.py` – ZIP/Manifest/Sicherheitsinvarianten.
- `tests/test_payback_data.py` – Read-Scoping und Kennzahlen.

## Implementierungsreihenfolge

### Task 1: Vertrag und Migration

- [x] Migrationstest schreiben und RED bestätigen.
- [x] Flow-Tabelle und optionale Einkaufsbetragsfelder implementieren.
- [x] Strikte Pydantic-Schemas mit unbekannten Feldern verboten und Listenlimits ergänzen.
- [x] Migration/Schematests GREEN.

### Task 2: Sicherer Pairing- und Importpfad

- [x] Tests für Start, HMAC-at-rest, Ablauf, Einmalverbrauch, generische Fehler und Haushaltsbindung schreiben (RED).
- [x] Pairingcode mit mindestens 256 Bit Entropie und zehn Minuten TTL implementieren.
- [x] PAYBACK-Verbindung ohne Providercredential dediziert erstellen/aktualisieren.
- [x] Normalisierten Payload in einer Transaktion via bestehender Loyalty-Persistenz speichern.
- [x] Idempotenz und konkurrierenden Doppelverbrauch testen (GREEN).

### Task 3: Read-API und Einkaufskennzahlen

- [x] Tests für private/haushaltsweite Sichtbarkeit und fremden Zugriff schreiben (RED).
- [x] Datenendpoint mit begrenzten Listen und neuestem Punktestand implementieren.
- [x] Kennzahlen implementieren: Aktivitätsanzahl, Partnerhäufigkeit, Punkte gesammelt/eingelöst, sichtbarer Einkaufsumsatz und Couponstatus.
- [x] Tests GREEN.

### Task 4: Browsererweiterung

- [x] Sicherheitstests für Manifest und Paketinhalt schreiben (RED).
- [x] Manifest V3 mit PAYBACK-Leserechten und optionaler HydraHive-Hostpermission erstellen.
- [x] Punktestand/Verfall, Aktivitäten und Coupons defensiv extrahieren und lokal deduplizieren.
- [x] Vorschau, Seitenstatus, Senden und anschließendes Löschen implementieren.
- [x] Kein Cookie-/webRequest-Recht, kein Remote-Code, kein Mutation-/Aktivierungscode.
- [x] Reproduzierbares ZIP und SHA-256 liefern; Tests GREEN.

### Task 5: Haushaltsbuch-Frontend

- [x] API-Typen und Clientmethoden ergänzen.
- [x] Bridge-Dialog mit Extension-Download, Einmalcode, Ablauf und Importpolling implementieren.
- [x] PAYBACK-Verbindungskarte auf „Browser-Import“ statt Provider-Sync umstellen.
- [x] Read-only Datenansicht mit Kennzahlen, Aktivitäten, Verfall und Coupons implementieren.
- [x] Frontend-Build GREEN.

### Task 6: Abschluss

- [x] Security-Audit: Token, öffentlicher Endpoint, Extensionpermissions, CORS, Logs, Limits.
- [x] HH-Review und Dateigrößenprüfung.
- [x] Gesamttests und Frontend-Build.
- [x] Manifest-Version auf 1.5.0 erhöhen.
- [x] Source-PR #58 erstellt und nach grüner Verifikation zur Zusammenführung vorbereitet.

## Akzeptanzkriterien

- [x] Keine PAYBACK-Passwörter, Cookies, Tokens, App-Secrets oder Roh-HTML erreichen HydraHive.
- [x] Einmalcode ist hochentropisch, gehasht, kurzlebig, eigentümergebunden und einmalig.
- [x] Alle sichtbaren und eindeutig parsebaren Einkaufsverhaltensdaten werden normalisiert übernommen.
- [x] Wiederholte Erfassung ist idempotent.
- [x] Private Daten bleiben privat; Haushaltssichtbarkeit funktioniert bewusst.
- [x] Nur lesende UI und Extension; keine PAYBACK-Aktion.
- [x] Tests, Ruff, Reviews und Build sind grün.

## Nicht in diesem Plan

- automatische Hintergrundsynchronisierung;
- private mobile PAYBACK-API;
- Couponaktivierung, Punkteeinlösung oder Kartenbarcode;
- garantierte Artikelpositionen, wenn PAYBACK sie nicht sichtbar bereitstellt;
- Firefox-Paketierung in V1.
