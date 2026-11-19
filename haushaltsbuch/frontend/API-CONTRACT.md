# Haushaltsbuch V1–V4 – Frontend/Backend-Vertrag

Basis: `/api/modules/haushaltsbuch` (im Frontend-Client ohne `/api`). JSON-Felder sind `snake_case`. Geldwerte sind ausnahmslos Integer-Minor-Units; Kurse sind Dezimalstrings. Änderbare Ressourcen liefern und verlangen `revision`. Veraltete Revisionen antworten mit HTTP 409. Unbekannte oder haushaltsfremde IDs antworten mit 404.

## Haushalt

- `GET /household` → Haushalt inklusive `current_role` und `members`; 404 bedeutet noch kein Haushalt.
- `POST /household` → Haushalt; Body `name`, `base_currency`, `timezone`, `create_default_categories`.
- `PUT /household` → Haushalt; Create-Felder plus `revision`. Die Basiswährung ist in V1 nach dem Anlegen unveränderlich.
- `POST /household/members` → Mitglied; Body `{username}` (exakte Suche).
- `DELETE /household/members/{id}?revision=n` → 204.
- `POST /household/ownership` → neues Eigentümer-Mitglied; Body `{member_id, revision}`.
- `GET|POST /household/invites`; Erzeugung mit `{expires_in_hours:24}` liefert den Klartextcode genau in dieser Response.
- `DELETE /household/invites/{id}?revision=n` → 204.
- `POST /household/invites/accept` mit `{code}`.
- `GET /household/export` → vollständiges JSON inklusive Audit, ohne Token-Hashes.
- `POST /household/delete` mit `{confirmation:"DELETE", household_name}` → 204. POST ist bewusst gewählt, weil die Core-Clientabstraktion keinen Body für DELETE unterstützt und die doppelte Bestätigung Teil des Vertrags ist.

## Finanzdaten

- `GET|POST /accounts`, `PUT /accounts/{id}`; Listenfilter `include_archived`.
- `GET|POST /categories`, `PUT /categories/{id}`; Listenfilter `include_archived`.
- `GET|POST /transactions`, `GET /transactions/{id}`; Listenfilter `date_from`, `date_to`, `account_id`, `category_id`, `query`, `limit`, `offset`.
- `POST /transactions/{id}/reverse` mit `{revision}`. Buchungen werden nie hart gelöscht.
- `GET|POST /budgets`, `PUT /budgets/{id}`; Listenfilter `active_only` und `on_date`. Responses enthalten `available_amount`, Periodensnapshots und separat ausgewiesene rückwirkende Anpassungen.
- `GET|POST /recurring`, `PUT /recurring/{id}`; Listenfilter `include_inactive`.
- `GET /forecast?days=30|90|365`.
- `GET /dashboard` → `total_balance`, Monats-Einnahmen/-Ausgaben, Budgetsummen, nächste Fälligkeiten, 30-/90-Tage-Prognose und letzte Buchungen.
- `GET /audit?limit=n&offset=n` → Audit-Ereignisse.

## Bankimport-Inbox

- `GET|POST /import-profiles`, `PUT|DELETE /import-profiles/{id}` verwalten haushaltsgebundene CSV-Mappings.
- `POST /imports` ist Multipart mit `file`, `account_id`, `format=auto|camt|mt940|csv|pdf|paypal`, optional `mapping` als JSON und optional `profile_id`. CSV-Datumswerte im deutschen Punktformat akzeptieren pro Zelle sowohl zwei- als auch vierstellige Jahreszahlen.
- `GET /imports` liefert Paketzusammenfassungen; `GET /imports/{id}` zusätzlich normalisierte Zeilen.
- `DELETE /imports/{id}?revision=n&rows_revision=n` löscht ausschließlich unveränderte, noch nicht gebuchte Entwürfe samt Zeilen; gebuchte Historie bleibt unveränderlich.
- `PATCH /imports/{id}/rows/{row_id}` ändert Entscheidung, Kategorie und korrigierbare Metadaten mit `revision`.
- `POST /imports/{id}/complete` mit `{revision}` bucht alle akzeptierten Zeilen atomar.
- `POST /imports/{id}/reverse` mit `{revision}` storniert das gesamte Paket über Gegenbuchungen.
- Uploads erzeugen ausschließlich Entwürfe. Fehlerzeilen bleiben sichtbar, starke Duplikate sind standardmäßig ausgeschlossen.

### PDF-Kontoauszug und PayPal-CSV (V9 Phase 2)

- `format=pdf` — Bank-Kontoauszug mit Textschicht. Auto-Erkennung an der Signatur `%PDF-`.
  Extraktion ausschließlich über die lokale Sandbox (pdfinfo/pdftotext unter bwrap+prlimit),
  kein ungesicherter Fallback. Maximal 50 Seiten. Fehlercodes (422): `pdf_no_text_layer`
  (Scan-PDF ohne Text — Hinweis: Beleg-Erkennung oder CSV/CAMT-Export der Bank nutzen),
  `pdf_unreadable` (beschädigt/verschlüsselt), `pdf_too_many_pages`, `pdf_no_transactions`
  (Text vorhanden, aber keine Buchungszeile erkannt), `pdf_extraction_unavailable`
  (Sandbox/pdftotext fehlt auf dem Server). Zeilen ohne eindeutiges Datum/Betrag erscheinen
  als eigene Zeile mit `errors=["pdf_line_ambiguous"]` statt geraten zu werden; solche Zeilen
  haben kein `bank_reference` (Fingerprint `weak`).
- `format=paypal` — offizieller PayPal-Aktivitäten-CSV-Export. Auto-Erkennung an den
  Header-Spalten (`Transaktionscode`/`Transaction ID` + `Brutto`/`Gross`). Deutsche und
  englische Spaltennamen, Komma- oder Punkt-Dezimaltrennzeichen, Encoding `utf-8-sig` oder
  `cp1252`. Brutto ist die Hauptzeile (`bank_reference` = Transaktionscode, Fingerprint
  `strong`); eine Gebühr ≠ 0 erscheint als eigene Zeile (`purpose` „PayPal-Gebühr …“,
  `bank_reference` „`<Transaktionscode>:fee`“). Währungsumrechnungszeilen („Allgemeine
  Währungsumrechnung“/„General Currency Conversion“) werden verworfen und als Warnung
  `paypal_currency_conversion_discarded` an der vorherigen Zeile vermerkt. Nur Status
  „Abgeschlossen“/„Completed“ wird übernommen; andere Status ergeben eine Fehlerzeile mit
  `errors=["paypal_status_not_completed"]`. Fehlercode (422): `paypal_header_invalid`
  (Pflichtspalten fehlen). Fremdwährungszeilen behalten ihre Originalwährung; die bestehende
  Kontowährungs-Prüfung (`account_currency_mismatch`) des Prüfbereichs greift unverändert.

## Crypto-Brücke (V9 Phase 3)

NUR lesend über den Cryptoboard-Read-Port. Kein Kurs-Client in diesem Modul, keine
Cryptoboard-Interna. Geld ausschließlich Integer-Minor-Units; Krypto-Mengen bleiben Text
(Decimal-String) in `purpose`, nie als eigenes Zahlenfeld.

- `GET /crypto-bridge/status` → `{available, reason, portfolios}`. `reason` nur gesetzt wenn
  `available=false` (`module_missing`/`module_not_loaded`/`port_incompatible`); `portfolios`
  sind ausschließlich die eigenen des anfragenden Users, bei `unavailable` leer.
- `GET /accounts` (bestehend) — jede Zeile zusätzlich: `linked_portfolio_id` (string|null,
  nur befüllt wenn `linked_by_me`), `linked_by_me` (bool), `crypto_linked` (bool).
- `PUT /accounts/{id}/crypto-link` body `{portfolio_id, revision}` → Account. Nur für
  `type=wallet`, nicht archiviert, Portfolio-ID muss im eigenen `portfolios_for` enthalten
  sein, ein Konto max. ein Portfolio. 422 `crypto_wallet_required`, 404
  `crypto_portfolio_not_found`, 409 `crypto_account_linked`, 422
  `crypto_currency_unsupported` (Haushalt oder Konto nicht EUR).
- `DELETE /accounts/{id}/crypto-link?revision=n` → Account. Durch den Verknüpfer oder den
  Haushalts-Owner; löscht den Snapshot, der gebuchte `balance_base` bleibt unverändert.
- `GET /accounts/{id}/crypto-value` → `{account_id, state, value_minor, as_of, complete,
  booked_balance, reason}`. `state`: `"unlinked"` | `"hidden"` (von einem anderen Mitglied
  verknüpft — kein Live-Wert, Port wird nicht aufgerufen) | `"live"` (Port erfolgreich,
  Snapshot aktualisiert) | `"stale"` (Port/Portfolio nicht verfügbar, letzter Snapshot,
  `value_minor` ggf. `null`, `reason` gesetzt).
- `POST /crypto-bridge/trade-imports` body `{wallet_account_id, fiat_account_id,
  fee_category_id?, since?}` → ImportBatch wie `POST /imports` (Status `draft`,
  `source_format="crypto_trades"`, `account_id=fiat_account_id`, `display_filename
  ="Cryptoboard-Trades"`, zusätzlich `warnings.skipped_transfers`). Nur der Verknüpfer des
  Wallets; `fiat_account_id` muss ein nicht-internes, nicht-wallet Konto sein;
  `fee_category_id` (falls gesetzt) muss eine expense-Kategorie sein. Je Trade: `buy`/`sell`
  erzeugen eine Transferzeile (`counter_account_id` = Wallet, `purpose` „Kauf/Verkauf <Menge>
  <SYMBOL>“, `bank_reference=<ref>`) plus bei Gebühr ≠ 0 eine zweite Zeile
  (`bank_reference=<ref>:fee`, `category_id=fee_category_id`); `transfer_in`/`transfer_out`
  werden nicht importiert (zählen in `warnings.skipped_transfers`). 422
  `crypto_wallet_not_linked`, 403 `crypto_link_owner_only`, 422
  `crypto_fiat_account_invalid`, 422 `crypto_fee_category_invalid`, 404
  `crypto_portfolio_not_found`, 422 `crypto_bridge_unavailable`.
- Abschluss über das bestehende `POST /imports/{id}/complete`: Zeilen mit
  `counter_account_id` werden als Konto↔Konto-Buchung gebucht (keine Kategorie nötig),
  `POST /imports/{id}/reverse` storniert sie korrekt. `ImportRow`-JSON hat zusätzlich
  `counter_account_id` (int|null).
- Zugriffsschutz: Verknüpfte Konten anderer Mitglieder zeigen nie die Portfolio-ID oder einen
  Live-Wert; der Port wird ausschließlich mit dem Username des verknüpfenden Users
  aufgerufen, nie mit dem eines anderen Mitglieds.

## Kundenkarten-Fundament (V4.0)

- `GET /loyalty/connections` listet für Mitglieder sichtbare Verbindungen. Private Verbindungen sind nur für den Besitzer und den Haushaltseigentümer sichtbar.
- `POST /loyalty/connections` legt nach erfolgreichem Provider-Callback eine Verbindung an. Der Body referenziert ein vorhandenes verschlüsseltes Credential; Provider-Konto-IDs werden nur gehasht gespeichert und nie zurückgegeben.
- `PUT /loyalty/connections/{id}` ändert Alias/Sichtbarkeit mit `revision`.
- `DELETE /loyalty/connections/{id}?revision=n` trennt die Verbindung und löscht synchronisierte Loyalty-Daten. Ein vom Lidl-Assistenten erzeugtes Connector-Credential wird ebenfalls gelöscht; manuell referenzierte Vault-Credentials bleiben bestehen.
- `POST /loyalty/connections/{id}/sync` startet genau einen manuellen read-only Sync. Deaktivierte/nicht registrierte Provider, laufende Syncs und Cooldowns werden serverseitig abgewiesen.
- `GET /loyalty/connections/{id}/sync-runs` liefert maximal 100 redigierte Läufe ohne Secrets oder Provider-Payloads.

## Experimenteller Lidl-Testconnector (V4.1)

- `GET /loyalty/provider-status` meldet den Connectorstatus. Lidl ist ohne zusätzliche Installationskonfiguration standardmäßig aktiv; Betreiber können ihn bei Bedarf ausdrücklich mit `HH_HAUSHALTSBUCH_LIDL_ENABLED=0` als Not-Aus deaktivieren.
- `POST /loyalty/lidl/auth/start` verlangt `{accepted_experimental_risk:true,country_code:"DE",language_code:"de"}` und liefert eine feste Lidl-Authorize-URL, einen verschlüsselten Flow-Token und die Ablaufzeit.
- Passwort und MFA-Code werden ausschließlich direkt bei Lidl eingegeben. `POST /loyalty/lidl/auth/complete` erhält nur `{flow_token,callback_url,alias?,visibility}`. Die Callback-URL muss dem gestarteten, höchstens zehn Minuten alten `com.lidlplus.app://callback`-Flow entsprechen; die browserspezifischen sicheren Formen `callback?…` und `callback/?…` sowie Lidls exakt erwarteter `scope`-Rückgabeparameter werden akzeptiert.
- Das Refresh-Token liegt ausschließlich AES-GCM-verschlüsselt im zentralen Credential-Store. Ein beim Login oder Refresh ausgestelltes Access-Token bleibt nur bis zu seinem Provider-Ablauf und nur im Arbeitsspeicher; beim Trennen wird es sofort entfernt. Tokenrequests authentifizieren den nativen Client ausschließlich per Basic-Header; `client_id` wird nicht zusätzlich im Form-Body dupliziert.
- `GET /loyalty/receipts` listet maximal 500 sichtbare, normalisierte Belege; `GET /loyalty/receipts/{id}` ergänzt Artikel und Adjustments. Rohpayloads und HTML-Belege werden nicht persistiert.
- Lidl-Sync ist manuell, read-only und auf DE/de sowie maximal 200 Belege pro Lauf begrenzt. PAYBACK bleibt weiterhin deaktiviert.
- Der read-only Abruf sendet den aktuellen Android-Ticketvertrag mit realer Clientversion `16.43.4`, Android-Paket-/Geräteheadern und einer stabilen, nicht personenbezogenen Device-ID pro Verbindung. Ein Ticket-401 wird genau einmal mit frisch rotiertem Token wiederholt; nur eine Ablehnung am Tokenendpoint verlangt eine Neuanmeldung. Verbindungen mit dem alten generischen Zustand `reauth_required/auth_required` können genau einmal manuell über „Anmeldung erneut prüfen“ migriert werden.
- Die Schnittstelle ist inoffiziell und experimentell. Es gibt keine Stabilitäts- oder Zulässigkeitszusage; CAPTCHA, WAF, Device Attestation und Rechtstextdialoge werden nicht automatisiert oder umgangen.

## Auswertungen (V9 Phase 1)

Reine Lese-Aggregate, read-only, keine neuen Felder in bestehenden Ressourcen. Alle Beträge
Integer-Minor-Units, Prozentanteile Integer-Basispunkte (10000 = 100 %). Vertrag im Detail:
`PHASE1-REPORTS-CONTRACT.md` (Orchestrierungs-Dokumentation außerhalb des Moduls).

- `GET /reports/cashflow` — Einnahmen/Ausgaben je Monat.
- `GET /reports/net-worth` — kumulierter Saldo aller nicht-internen Konten je Monatsende.
- `GET /reports/categories` — Ausgaben-Verteilung je Hauptkategorie, mit `parent_id` Drilldown auf Unterkategorien.
- `GET /reports/budgets` — Soll/Ist je aktivem Budget und Monat (dieselben Hilfen wie `GET /budgets`).
- `GET /reports/fixed-costs` — feste vs. variable Ausgaben je Monat (Heuristik über `recurring`-Regeln).

Gemeinsame Query-Parameter: `range=3|6|12|24|all` (Default `12`), `format=json|csv` (Default `json`).
Ungültiger `range`-Wert → 422. CSV: Semikolon-getrennt, dieselben Zeilen wie `rows`, Minor-Units-Integer,
`Content-Disposition: attachment`, CSV-Injection-Schutz für Textfelder. Jede JSON-Antwort hat den Rahmen
`{report, range, currency, start_month, end_month, rows, totals}`; Monate ohne Daten erscheinen mit 0
(lückenlose Zeitreihe). Noch nicht umgesetzt: PDF-Export, PayPal-Abgleich (Phase 2), Krypto-Erweiterung
der Vermögensübersicht (Phase 3).

Create/Update-Payloads und Responses sind in `types.ts` beziehungsweise `loyaltyTypes.ts` vollständig typisiert. Die Clients stehen in `api.ts` und `loyaltyApi.ts`.
