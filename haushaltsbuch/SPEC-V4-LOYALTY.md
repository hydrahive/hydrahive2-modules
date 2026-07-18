# SPEC V4 — Lidl Plus und PAYBACK

Status: geplant, noch nicht implementiert  
Stand: 18. Juli 2026

## 1. Ziel

Das Haushaltsbuch erhält eine providerneutrale Kundenkarten-Plattform mit zwei
konkreten Verbindungen:

1. **Lidl Plus:** digitale Kassenbons samt Artikelpositionen, Rabatten, Coupons
   und Pfand direkt synchronisieren und mit Bankbuchungen verknüpfen.
2. **PAYBACK:** Punktestand, Punkteverfall, Punkteaktivitäten, Coupons und Partner
   direkt synchronisieren und mit Buchungen beziehungsweise Belegen verknüpfen.

Die Verbindungen sind echte Online-Synchronisierungen. **Nicht Bestandteil:**
E-Mail-, PDF-, OCR- oder sonstige Dateiimporte.

## 2. Produktprinzipien

- Nur nach explizitem Opt-in und interaktiver Anmeldung.
- Read-only gegenüber Lidl/PAYBACK in V1.
- Niemals Passwort oder MFA-Code speichern.
- Keine CAPTCHA-, 2SV-, Attestation- oder Bot-Schutz-Umgehung.
- Providerdaten erzeugen keine stillen Ledger-Buchungen.
- Matches sind nachvollziehbare Vorschläge und müssen bestätigt werden.
- Alle Providerdetails bleiben hinter austauschbaren Adaptern.
- Jede Verbindung besitzt Feature-Flag, Kill-Switch und redigierten Sync-Verlauf.
- Fehlende Provider-Fähigkeiten werden ehrlich angezeigt, nicht simuliert.

## 3. Machbarkeitsentscheidung

### Lidl Plus

Technisch plausibel als experimenteller read-only Connector. Community-Quellen
belegen OIDC/OAuth mit PKCE, erneuerbare Tokens und Ticket-Endpunkte. Es gibt aber
keine öffentliche stabile Lidl-API. Vor Live-Implementierung sind rechtliche
Freigabe und ein begrenzter Spike Pflicht.

### PAYBACK

Keine dokumentierte öffentliche Endkunden-API gefunden. Die vorhandene
Reverse-Engineering-Referenz ist alt, unvollständig, ohne Lizenz und benötigt aus
der App extrahierte Client-Credentials. Das providerneutrale Fundament kann
gebaut werden; der Live-Adapter wird nur aktiviert, wenn der Spike einen
zulässigen, erneuerbaren und read-only Zugriff ohne Schutzumgehung bestätigt.

Die bisherige ROADMAP-Referenz `dduarte.github.io/Payback/api.html` ist fachlich
falsch und darf nicht verwendet werden.

## 4. Nutzerrollen und Sichtbarkeit

- Eine Verbindung gehört einem Haushaltsmitglied (`owner_member_id`).
- Owner und Verbindungsbesitzer dürfen verbinden, reauthentifizieren, manuell
  synchronisieren, trennen und die Sichtbarkeit ändern.
- Standard: Nur Verbindungsbesitzer sieht detaillierte Artikel-/Punkteaktivitäten.
- Haushaltsweite Freigabe muss separat bestätigt werden.
- Alle Zugriffe werden serverseitig gegen Haushalt und Rolle geprüft.
- Verknüpfte Ledger-Transaktionen folgen weiterhin den Haushaltsbuchrechten.

## 5. UI

Neue Hauptansicht **Kundenkarten** mit:

### Übersicht

- Karten pro Anbieter und Mitglied
- Status: Verbinden, Aktiv, Sync läuft, Reauth erforderlich, Blockiert, Deaktiviert
- letzter erfolgreicher Sync, nächster geplanter Sync, letzter Fehler
- manueller Sync und Trennen
- Hinweis „experimentelle inoffizielle Verbindung“, solange keine offizielle API
  vorliegt

### Lidl Plus

- Bonliste: Datum, Filiale, Betrag, Matchstatus
- Bondetail: Artikel, Menge, Einzel-/Gesamtpreis, Rabatt, Coupon, Pfand,
  Summenprüfung und Parserwarnungen
- Bankmatch-Vorschlag mit Score und Gründen
- Match bestätigen, anderen Kandidaten wählen oder ablehnen
- Artikelpositionen vorhandenen Haushaltsbuchkategorien zuordnen; Zuordnung als
  lernbare Artikel-/Händlerregel speichern
- Sync-Verlauf und Reauth-Banner

### PAYBACK

- aktueller Punktestand und nächster Punkteverfall
- Aktivitäten: Gutschrift, Einlösung, Verfall, Storno, Anpassung
- Coupons mit Partner, Laufzeit und Status, read-only
- Partnerübersicht
- Match-Vorschläge zu Belegen/Bankbuchungen mit Gründen
- Sync-Verlauf und Reauth-Banner

V1 besitzt **keinen** Button zum Aktivieren von Coupons oder Einlösen von Punkten.

## 6. Provider-Fähigkeiten

Jeder Adapter liefert `ProviderCapabilities`:

- `receipts`, `receipt_items`, `discounts`, `deposits`
- `balance`, `expirations`, `activities`, `coupons`, `partners`
- `scheduled_sync`, `token_refresh`, `remote_revoke`
- Schreibfähigkeiten werden in V1 nicht angeboten.

UI und Sync-Engine verwenden ausschließlich gemeldete Fähigkeiten.

## 7. Datenmodell

Migration 004 führt folgende Tabellen ein:

### `module_haushaltsbuch_loyalty_connections`

- Haushalt, Provider (`lidl_plus|payback`), Besitzer-Mitglied
- Credential-Referenz und maskierte Konto-/Kartendarstellung
- Alias, Land, Sprache, Sichtbarkeit
- Status, Capabilities JSON, Feature-Flag, Sync-Konfiguration
- Cursor, letzter Sync/Fehler, Revisions- und Zeitfelder
- Unique: `(household_id, provider, owner_member_id, account_fingerprint)`

### `module_haushaltsbuch_loyalty_sync_runs`

- Verbindung, Trigger (`manual|scheduled`), Start/Ende, Status
- Cursor vorher/nachher, Zähler und redigierter Fehlercode
- nächster erlaubter Versuch; keine Tokens oder Payloads

### `module_haushaltsbuch_receipts`

- Verbindung, Quelle, Provider-Beleg-ID, Fingerprint
- Händler/Filiale, Kaufzeitpunkt/Zeitzone, Betrag/Währung, Zahlungsart
- Rabatt-/Coupon-/Pfandsummen, Steuersummen, Validierungsstatus
- Provider-/Seen-Zeitfelder, Inhalts-Hash, Remote-Status
- Unique: `(connection_id, provider_receipt_id)`

### `module_haushaltsbuch_receipt_items`

- Beleg, Provider-Reihenfolge, Original-/Normalname, GTIN/EAN
- Menge/Einheit, Einzel-/Gesamtbetrag, Steuergruppe
- Typ (`product|deposit|discount|coupon|return|adjustment`)
- Kategorie-Vorschlag und bestätigte Kategorie
- Parserwarnungen

### `module_haushaltsbuch_loyalty_balances`

- Verbindung, Beobachtungszeit, verfügbare Punkte, optional versionierter
  Geldgegenwert, Fingerprint

### `module_haushaltsbuch_loyalty_activities`

- Provider-Aktivitäts-ID/Fingerprint, Art, Datum, Punkteänderung
- Partner, Originalbeschreibung, Provider-/Seen-Zeitfelder
- Unique pro Verbindung und Provider-ID/Fingerprint

### `module_haushaltsbuch_loyalty_expirations`

- Verbindung, Verfallsdatum, Punkte und Status

### `module_haushaltsbuch_loyalty_partners`

- Provider, Provider-Partner-ID, Name, Aktivstatus, Seen-Zeitfelder

### `module_haushaltsbuch_loyalty_coupons`

- Verbindung, Provider-Coupon-ID/Fingerprint, Partner
- Titel/Beschreibung, Laufzeit, Aktivierungsstatus
- Multiplikator/Bonuspunkte/Bedingung, Seen-Zeitfelder, Remote-Status

### `module_haushaltsbuch_external_matches`

- Verbindung und Quellobjekt (`receipt|loyalty_activity`)
- Ziel (`transaction|receipt`), Score, Algorithmusversion, Gründe JSON
- Status (`suggested|confirmed|rejected`), bestätigendes Mitglied
- Eindeutigkeitsregeln verhindern konkurrierende bestätigte Zuordnungen

### `module_haushaltsbuch_item_category_rules`

- Haushalt, Provider, GTIN oder normalisierter Artikel-/Händlerschlüssel
- Kategorie, Trefferzahl, letzte Bestätigung
- manuell bestätigte Regeln haben Vorrang vor LLM-Vorschlägen

## 8. Secrets und Authentifizierung

- Credential-Werte werden ausschließlich über Hydras zentralen Credential-Store
  gespeichert (`AES-GCM`, atomisches Schreiben, Datei `0600`).
- Die Modul-DB speichert nur `credential_ref`.
- Für Lidl wird nach verifiziertem PKCE-Flow nur das Refresh-Token gespeichert;
  Access-Token bleibt im Speicher. Rotierte Refresh-Tokens werden atomar ersetzt.
- PAYBACK folgt demselben Modell, falls der Spike einen erneuerbaren Token liefert.
  Passwort-/Cookie-Dauerpersistenz ist kein akzeptierter Zielzustand.
- OAuth `state`, `nonce` und PKCE-Verifier sind kurzlebig, an User und Verbindung
  gebunden und nur einmal verwendbar.
- Keine Secrets in URL, Log, Audit, Exception, Telemetrie oder Test-Fixture.

## 9. Adaptervertrag

Providerneutrale Ports:

```text
connect_interactive(connection, callback) -> ConnectionStatus
probe(connection) -> ProviderCapabilities
refresh_auth(connection) -> TokenMetadata
sync_receipts(connection, cursor, limit) -> ReceiptPage
sync_balance(connection) -> Balance
sync_expirations(connection) -> list[Expiration]
sync_activities(connection, cursor, limit) -> ActivityPage
sync_coupons(connection, cursor, limit) -> CouponPage
sync_partners(connection) -> list[Partner]
disconnect(connection) -> DisconnectResult
```

Nicht unterstützte Methoden liefern `CapabilityUnavailable`, nicht leere
Scheindaten. Adapter verwenden feste Host-/Redirect-Allowlists, TLS-Verifikation,
Timeouts, Antwortgrößen-, Pagination- und Requestlimits.

Fehlerklassen: `AuthRequired`, `ForbiddenOrBlocked`, `RateLimited`,
`ProviderUnavailable`, `SchemaChanged`, `RemoteObjectGone`,
`InvalidProviderData`, `CapabilityUnavailable`.

## 10. Synchronisation

### Gemeinsamer Ablauf

1. Berechtigung, Feature-Flag und Verbindungsstatus prüfen.
2. DB-Lock pro Verbindung erwerben.
3. Token bei Bedarf genau einmal erneuern.
4. Fähigkeiten abfragen.
5. Providerdaten sequentiell und paginiert lesen.
6. Strikt normalisieren/validieren; Geld niemals als `float`.
7. Idempotent upserten und fachliche Änderungen auditieren.
8. Matches berechnen, aber nicht automatisch bestätigen.
9. Cursor erst nach erfolgreicher Seite fortschreiben.
10. Sync-Lauf redigiert abschließen und Lock freigeben.

### Betriebsregeln

- MVP nur manueller Sync.
- Später höchstens täglich, nur Opt-in, mit Jitter.
- `429`: `Retry-After`; `5xx`: begrenzter exponentieller Backoff.
- `401`: einmal Refresh; erneut `401` → `reauth_required`.
- `403`/Accountwarnung → `blocked`, sofortiger Stop.
- Keine parallelen Detailabrufe im MVP.
- Harte Zeit-, Seiten- und Requestbudgets verhindern Schleifen.
- Überlappungsfenster bei jedem Lauf, da Provider-Cursor nicht garantiert sind.
- Remote verschwundene Daten erst nach mehreren Läufen markieren, nie sofort hart
  löschen.

## 11. Lidl-Belegnormalisierung

Belegkopf und Positionen folgen einem kanonischen Vertrag. Unterstützt werden:

- Minor-Unit-Beträge, ISO-Währung, Originalzeitzone
- strukturierte Artikel, Dezimalmengen und Wiegeware
- Rabatte/Coupons als Adjustments
- Pfand separat von Waren
- Retouren/negative Positionen
- Summenabgleich `Positionen + Adjustments = Beleggesamtbetrag`

Fehlende Pflichtfelder oder unerklärte Summenabweichung ergeben `needs_review`.
Rohpayloads werden standardmäßig nicht dauerhaft gespeichert.

## 12. Matching

### Lidl-Beleg → Banktransaktion

Pflicht: Ausgabe und gleiche Währung. Signale:

- exakter Betrag: +60
- Kauf-/Buchungsdatum 0/1/2/3 Tage: +25/+20/+12/+5
- normalisierter Lidl-Händler: +15
- passende datensparsame Zahlungsreferenz: +20
- bestätigte Barzahlung: Ausschluss

Nur eindeutig bester Kandidat über Mindestscore wird vorgeschlagen. Gleichstände
bleiben manuell. Score, Gründe und Algorithmusversion werden gespeichert.

### PAYBACK-Aktivität → Beleg/Buchung

- Partner-/Händleralias
- Aktivitätsdatum im konservativen Fenster
- Besitzer/Verbindung
- Punktzahl nur als Plausibilität, nie als alleiniger Schlüssel

PAYBACK-Aktivitäten erzeugen keine Ledger-Postings. Punktegegenwert und tatsächliche
Geldersparnis bleiben getrennte Kennzahlen.

## 13. Kategorisierung und Budgets

- Bestätigte Artikelregeln (GTIN/Artikelname) zuerst.
- Danach bestätigte Händlerhistorie.
- Optional LLM-Vorschlag nur für offene Artikelgruppen.
- Ein Lidl-Beleg kann mehrere Kategorien besitzen. Die bestätigte Aufteilung wird
  über Postings der verknüpften Transaktion umgesetzt; Summe muss exakt dem
  Transaktionsbetrag entsprechen.
- Pfand/Rabatt/Coupon werden nicht als normale Warenkategorie behandelt.
- Jede Änderung der Aufteilung erfordert Review und Optimistic Revision.

## 14. API

Basis: `/api/modules/haushaltsbuch`

### Verbindungen

- `GET /loyalty/connections`
- `POST /loyalty/connections/{provider}/connect/start`
- `POST /loyalty/connections/{provider}/connect/callback`
- `POST /loyalty/connections/{id}/reauth/start`
- `POST /loyalty/connections/{id}/sync`
- `PUT /loyalty/connections/{id}` (Alias, Sichtbarkeit, Zeitplan)
- `DELETE /loyalty/connections/{id}` (Revision + Löschmodus)
- `GET /loyalty/connections/{id}/sync-runs`

### Daten

- `GET /receipts`, `GET /receipts/{id}`
- `POST /receipts/{id}/match`, `DELETE /receipts/{id}/match`
- `PUT /receipts/{id}/items/{item_id}/category`
- `GET /loyalty/balances`
- `GET /loyalty/activities`
- `GET /loyalty/expirations`
- `GET /loyalty/coupons`
- `GET /loyalty/partners`
- `POST /loyalty/activities/{id}/match`

Alle mutierenden Endpunkte verwenden Revisionen; Isolation immer serverseitig.

## 15. Datenschutz und Sicherheit

- Datenminimierung und Zweckbindung auf Haushaltsbuch/Analyse/Matching.
- Keine Profil-, Standort-, Werbe- oder Trackingdaten abrufen.
- Artikelkäufe und Punkteaktivitäten standardmäßig mitgliedsprivat.
- Export, Trennen und Löschen mit verständlicher Aufbewahrungswirkung.
- Keine externe Telemetrie mit Finanz-/Einkaufsdaten.
- Provider-Code und Abhängigkeiten benötigen Lizenz-, Supply-Chain- und
  Security-Review.
- Feature-Flag/Kill-Switch pro Provider und Installation.
- Live-Zugriff nur nach dokumentierter rechtlicher/vertraglicher Freigabe.

## 16. Akzeptanzkriterien

### Provider-Fundament

- Zwei Verbindungen desselben Providers für verschiedene Mitglieder möglich.
- Haushalts-/Mitgliedsisolation vollständig getestet.
- Secrets stehen niemals in Modul-DB, API-Antworten, Logs oder Auditdetails.
- Wiederholter Sync erzeugt keine Duplikate.
- Crash/Retry verliert keinen Cursor und doppelt keine Daten.
- Reauth, Rate-Limit, Providerfehler und Kill-Switch sind sichtbar und sicher.

### Lidl Plus

- Interaktiver Login ohne Passwortpersistenz/Schutzumgehung.
- Digitale Bons, Positionen, Rabatte und Pfand werden korrekt normalisiert.
- Summen stimmen oder der Bon landet in `needs_review`.
- Eindeutiger Bankmatch kann bestätigt und rückgängig gemacht werden.
- Artikel können mehreren Kategorien zugeordnet werden.

### PAYBACK

- Live-Adapter nur bei erfülltem Machbarkeits-Gate.
- Punktestand, Verfall, Aktivitäten, Coupons/Partner nur nach gemeldeter Fähigkeit.
- Keine Couponaktivierung/Punkteeinlösung in V1.
- Aktivitätsmatches ändern keine Ledger-Beträge.

## 17. Nicht in V4

- E-Mail-, PDF-, OCR- oder Dateiimport
- automatische Couponaktivierung
- Punkteeinlösung
- Profiländerungen bei Lidl/PAYBACK
- automatisches Bestätigen von Matches
- CAPTCHA-/2SV-/Attestation-Umgehung
- öffentliche Zusage stabiler Providerunterstützung ohne offizielle API
