# PAYBACK-Integration — technische Vorprüfung

Stand: 18. Juli 2026. Scope: direkte Synchronisierung eines PAYBACK-DE-Kontos.
Explizit ausgeschlossen: E-Mail-, PDF- und Dateiimport.

## Kurzfazit

Eine produktionsreife direkte PAYBACK-Anbindung ist derzeit **nicht verlässlich
planbar**, weil keine dokumentierte öffentliche Endkunden-API, kein stabiler
OAuth-Client, keine Sandbox und keine Supportzusage auffindbar sind. Eine
inoffizielle Mobile-App-API ist reverse-engineert worden, aber die öffentliche
Referenzimplementierung ist alt, unvollständig, ohne Lizenz und verlangt aus der
App extrahierte Client-Credentials. Der Connector darf daher nur hinter einem
Provider-Adapter und zunächst als deaktivierter technischer Spike entstehen.

Verbindliche Produktgrenze:

- Phase 1 ausschließlich **read-only**: Punktestand, Verfall, Punkteaktivitäten,
  Coupons und Partner, soweit die Schnittstelle diese stabil liefert.
- Keine automatische Coupon-Aktivierung, keine Punkteeinlösung und keine
  Profiländerung.
- Keine Umgehung von CAPTCHA, 2-Schritt-Verifizierung, Device Binding,
  Attestation oder anderen Schutzmaßnahmen.
- Kein Speichern von Passwort oder MFA-Code. Falls kein benutzergeführter Login
  mit erneuerbarer Sitzung möglich ist, wird der Live-Connector nicht ausgeliefert.

## Korrektur der bisherigen Roadmap

Die in `ROADMAP.md` verlinkte URL
`https://dduarte.github.io/Payback/api.html` beschreibt ein Hochschulprojekt zur
Verwaltung privater Schulden zwischen Freunden. Sie hat nichts mit dem deutschen
PAYBACK-Bonusprogramm zu tun und darf nicht länger als technische Referenz gelten.

## Quellen und Evidenz

### Offizielle Quellen

- PAYBACK Startseite/Funktionen: https://www.payback.de/
- Login: https://www.payback.de/login
- Loginmöglichkeiten: https://www.payback.de/faq/loginmoeglichkeiten
- 2-Schritt-Verifizierung: https://www.payback.de/faq/2-schritt-verifizierung
- Loginprobleme: https://www.payback.de/faq/fehlermeldung-login
- Datenschutz: https://www.payback.de/info/datenschutz
- Unternehmens-/Partnerinformationen: https://www.payback.group/de/

Diese Quellen bestätigen Produktfunktionen und 2SV, aber keinen öffentlichen
Endkunden-API-Zugang.

### Inoffizielle technische Quelle

- Repository: https://github.com/theodm/python-coupons
- README: https://github.com/theodm/python-coupons/blob/main/README.md

Das Repository beschreibt Reverse Engineering der iOS-App per Frida und nennt
Endpunkte für `secureauthenticate`, `getaccountbalance`, `getcoupons` und
`activatecoupon`. Es benötigt aus der App extrahierte Basic-Auth-Daten und einen
`principal`-Wert. Letzter Push: März 2024; keine veröffentlichte Lizenz; keine
Sandbox; keine dokumentierte 2SV-, Token-Rotations- oder Verlaufssynchronisation.
Es ist nur Evidenz für frühere technische Machbarkeit, nicht als Abhängigkeit
oder stabiler Vertrag geeignet.

## Authentifizierung und Credentials

### Anforderungen an einen zulässigen Ziel-Flow

1. Nutzer startet „PAYBACK verbinden“ explizit im Haushaltsbuch.
2. Authentifizierung erfolgt interaktiv in einem sichtbaren Browser/App-Flow.
3. PAYBACK kontrolliert Passwort-, CAPTCHA- und 2SV-Eingabe. HydraHive erhält
   und speichert diese Werte nie.
4. Nach erfolgreicher Autorisierung wird nur eine erneuerbare Sitzung bzw. ein
   Refresh-Token in Hydras AES-GCM-verschlüsseltem Credential-Store gespeichert.
5. Die Haushaltsbuch-DB speichert nur `credential_ref`, Konto-Alias,
   Kartenkennung maskiert/gehasht, Besitzer-Mitglied, Status und Metadaten.
6. Bei 401 wird genau einmal erneuert; bei erneutem 401, 403 oder 2SV-Anforderung
   stoppt der Sync mit `reauth_required` oder `blocked`.
7. „Trennen“ löscht das lokale Secret und widerruft es, falls ein belastbarer
   Revocation-Endpunkt verifiziert wurde.

### Harte Stop-Bedingungen

Kein Live-Connector, wenn:

- PAYBACK-Passwort dauerhaft gespeichert werden müsste;
- 2SV/CAPTCHA/Device Binding automatisiert umgangen werden müsste;
- Client-Credentials nur durch fortlaufende Extraktion aus der App beschafft
  werden können;
- kein erneuerbarer read-only Sitzungsmechanismus existiert;
- Nutzungsbedingungen oder eine rechtliche Prüfung den Zugriff ausschließen.

## Gewünschte Provider-Fähigkeiten

Der Adapter meldet Fähigkeiten dynamisch; keine UI-Funktion darf nur aufgrund
unbestätigter Annahmen erscheinen.

- `account_balance`: aktueller verfügbarer Punktestand
- `expiring_points`: Punktebetrag und Verfallsdatum
- `activity_history`: Buchung, Gutschrift, Storno, Einlösung mit stabiler ID
- `coupons_read`: Coupons, Partner, Laufzeit, Aktivierungsstatus, Multiplikator
- `partners_read`: Partnerkennung und Anzeigename
- `coupon_activation`: für V1 immer `false`
- `points_redemption`: für V1 immer `false`

Fehlt eine Fähigkeit, zeigt die UI „vom Provider nicht verfügbar“ statt leere
oder erfundene Daten.

## Kanonisches Datenmodell

### Verbindung

`loyalty_connections`

- `id`, `household_id`, `provider = payback`, `owner_member_id`
- `credential_ref`, `account_alias`, maskierte Kartenkennung
- `country = DE`, `status` (`pending`, `active`, `reauth_required`, `blocked`,
  `disabled`, `error`)
- `capabilities_json`, `sync_enabled`, `last_sync_at`, `next_sync_at`
- `last_error_code`, `revision`, Timestamps

### Punktestände

`loyalty_balance_snapshots`

- `connection_id`, `observed_at`, `available_points`
- `cash_equivalent_minor` nur nach expliziter, versionierter Umrechnungsregel
- `source_fingerprint`; unique `(connection_id, observed_at, source_fingerprint)`

### Punkteaktivitäten

`loyalty_activities`

- `connection_id`, `provider_activity_id` oder stabiler Fingerprint
- `activity_date`, `posted_at`, `kind` (`earn`, `redeem`, `expire`, `reverse`,
  `adjust`), `points_delta`, `partner_id`, Originalbeschreibung
- optionale `transaction_id`/`receipt_id`, Matchstatus und Matchscore
- `provider_updated_at`, `first_seen_at`, `last_seen_at`
- unique `(connection_id, provider_activity_id)`; fehlt ID, kanonischer Hash

### Punkteverfall

`loyalty_expirations`

- `connection_id`, `expires_on`, `points`, `status`
- unique `(connection_id, expires_on)`

### Partner und Coupons

`loyalty_partners`: Provider-ID, Name, Logo-URL nur als externe Referenz,
`active`, `last_seen_at`.

`loyalty_coupons`: Provider-ID/Fingerprint, Partner, Titel, Beschreibung,
`valid_from`, `valid_until`, `activation_status`, Multiplikator bzw. Bonuspunkte,
Bedingungstext, `provider_updated_at`, `last_seen_at`, `remote_unavailable`.

Keine automatische Aktivierung in V1. Couponbilder und Marketingtracking werden
nicht lokal gespiegelt.

### Synchronisationsläufe und Matches

`loyalty_sync_runs`: Trigger, Status, Cursor vorher/nachher, Zähler, Dauer,
redigierter Fehlercode, nächster erlaubter Versuch.

`loyalty_activity_matches`: Aktivität, Transaktion/Beleg, Score,
Algorithmusversion, Gründe, Status (`suggested`, `confirmed`, `rejected`).

## Adapterarchitektur

Providerneutraler Port:

```text
connect_interactive(connection, callback) -> ConnectionStatus
probe(connection) -> ProviderCapabilities
get_balance(connection) -> Balance
list_expirations(connection) -> list[Expiration]
list_activities(connection, cursor, page_size) -> ActivityPage
list_coupons(connection, cursor, page_size) -> CouponPage
list_partners(connection) -> list[Partner]
refresh_auth(connection) -> TokenMetadata
disconnect(connection) -> DisconnectResult
```

Der PAYBACK-Adapter ist ein austauschbares Paket hinter diesem Interface. Routes
oder UI kennen keine Provider-Endpunkte. Anforderungen: Host-Allowlist,
TLS-Verifikation, begrenzte Antwortgröße, Timeouts, harte Pagination-/Request-
Budgets, kein dynamisches Abrufen beliebiger URLs, strukturierte Fehlerklassen,
Feature-Flag und globaler Kill-Switch.

## Synchronisationsablauf

1. Verbindung und Haushalts-/Mitgliedsberechtigung prüfen.
2. Pro Verbindung einen DB-basierten Lock erwerben.
3. Sitzung bei Bedarf genau einmal erneuern.
4. Provider-Fähigkeiten abfragen.
5. Punktestand und Verfall lesen.
6. Aktivitäten, Coupons und Partner nur bei gemeldeter Fähigkeit paginiert lesen.
7. Antworten normalisieren und strikt validieren.
8. Idempotent upserten; Cursor erst nach erfolgreicher Seite fortschreiben.
9. Nicht mehr gelieferte Coupons/Aktivitäten nie sofort löschen, sondern nach
   mehreren vollständigen Läufen `remote_unavailable` markieren.
10. Match-Vorschläge berechnen, aber keine Ledger-Buchung ändern.
11. Sync-Lauf redigiert abschließen.

MVP nur manueller Sync. Später maximal täglich mit Opt-in, Jitter und Backoff.
429 respektiert `Retry-After`; 5xx exponentiell; 403 stoppt sofort; keine Login-
oder MFA-Schleifen.

## Verknüpfung mit Haushaltsbuchdaten

PAYBACK-Aktivitäten sind **keine Geldbuchungen** und erzeugen keine Ledger-
Postings. Sie werden nur verknüpft.

Kandidaten für eine Punktegutschrift:

- bekannte Partner-/Händler-Aliasse;
- Aktivitätsdatum innerhalb `-2/+7` Tagen zur Bankbuchung oder zum Beleg;
- Punktebetrag plausibel, aber niemals allein entscheidend;
- gleiche PAYBACK-Verbindung bzw. Besitzer-Mitglied;
- bereits bestätigte konkurrierende Verknüpfungen ausschließen.

Nur eindeutige Treffer werden vorgeschlagen. Punkte-Einlösungen dürfen den
Buchungsbetrag nicht automatisch verändern. Der tatsächliche Geldrabatt wird nur
aus einem verknüpften Bon oder einer expliziten Buchungsinformation abgeleitet;
der Punktegegenwert bleibt eine getrennte Analysegröße.

Lidl-Plus-Belege und PAYBACK-Aktivitäten nutzen dieselbe generische Match-Tabelle,
können aber unabhängig voneinander existieren.

## UI-Plan

Neue Ansicht „Kundenkarten“:

- Kartenübersicht mit Provider, Besitzer, Status, letztem Sync und Warnungen;
- „PAYBACK verbinden“ mit Hinweis auf inoffiziellen/experimentellen Status;
- Punktestand, nächster Verfall und Sync-Button;
- Tabs „Aktivitäten“, „Coupons“, „Verfall“, „Verknüpfungen“, „Sync-Verlauf“;
- Couponanzeige read-only; kein Aktivierungsbutton in V1;
- Reauth-Banner mit explizitem Benutzerflow;
- Trennen-/Löschen-Dialog mit klarer Auswirkung auf lokale Daten;
- Fähigkeiten-basierte UI: nicht verfügbare Providerdaten werden erklärt.

## Datenschutz und Sicherheit

- Verbindung gehört standardmäßig einem Mitglied. Haushaltsweite Einsicht in
  Punkte-/Einkaufsdaten erfordert dessen explizite Freigabe.
- Secrets ausschließlich im zentralen Credential-Store; keine Passwörter,
  Tokens, Cookies oder MFA-Codes in DB, Logs, Auditdetails oder Telemetrie.
- Kontonummer nur maskiert; Vergleichskennung als haushaltsgebundener Hash.
- Datenminimierung: kein Profil, keine Standort-/Werbedaten, keine Bilder.
- Export, Trennen und Löschen müssen Herkunft und Aufbewahrungswirkung erklären.
- Fremdbibliotheken/Reverse-Engineering-Code nicht übernehmen, solange Lizenz,
  Wartungszustand und Security nicht geklärt sind.

## Teststrategie

Ohne Livekonto in CI:

- synthetischer Fake-Provider und redigierte Contract-Fixtures;
- Authstatus, einmaliger Refresh, 2SV/CAPTCHA/403/429/5xx/Timeout;
- Pagination, Duplikate, fehlende IDs, geänderte/verschwundene Datensätze;
- Punktevorzeichen, Verfall, Storno, Couponlaufzeiten und unbekannte Felder;
- Idempotenz bei Wiederholung und Crash vor Cursor-Commit;
- Haushalts-/Mitgliedsisolation und Secret-/PII-Leak-Tests;
- Matchfälle: eindeutig, mehrdeutig, falscher Partner, Zeitversatz, Einlösung;
- UI: capabilities, reauth, leerer Zustand, Syncfehler, Disconnect.

Live-Smoke nur manuell mit separatem Testkonto, minimalen Requests und
vorheriger Freigabe; keine echten Credentials oder Payloads in Fixtures.

## Phasen und Gates

### Phase 0 — Freigabe

Nutzungsbedingungen, Datenschutz, zulässigen read-only Zugriff und offiziellen
Partner-/API-Weg prüfen. Gate: dokumentierte Freigabe; sonst nur Fake-Adapter.

### Phase 1 — isolierter Spike

Mit Testkonto Auth/2SV, Token/Sitzung, Host/Endpunkte, Punktestand, Verfall,
Aktivitäten, Coupons, Pagination und Rate-Limit-Verhalten verifizieren. Keine
Mutation. Gate: reproduzierbarer Login ohne Passwortspeicherung/Schutzumgehung,
erneuerbare Sitzung und stabile IDs/Schemata.

### Phase 2 — Provider-Fundament + Fake-Adapter

Generisches Datenmodell, Ports, Sync-Engine, UI, Credential-Referenz und Tests.
Gate: vollständige Contract-/Security-/Isolationstests.

### Phase 3 — experimenteller PAYBACK-Read-only-Adapter

Feature-Flag, manueller Sync, Punktestand/Verfall/Aktivitäten/Coupons soweit
verifiziert; Pilotgruppe. Gate: mehrere Wochen ohne Sperren, Datenverlust,
Duplikate oder breite Schemafehler.

### Phase 4 — begrenzte Beta

Optional täglicher Sync, Monitoring ohne PII, Kill-Switch und Wartungsprozess.
Schreibende Funktionen bleiben außerhalb V1 und brauchen eine eigene Freigabe.

## Stop-Kriterien

Sofort stoppen/deaktivieren bei rechtlichem Verbot, Passwortpersistenz,
notwendiger CAPTCHA-/2SV-/Attestation-Umgehung, App-Credential-Extraktion als
Dauerbetrieb, Account-Sperre/Warnung, wiederholtem 403, instabilen Beträgen oder
Punktedaten, Secret-/PII-Leak, nicht begrenzbaren Retry-Schleifen, ungeklärter
Lizenz oder fehlender Wartungsverantwortung.
