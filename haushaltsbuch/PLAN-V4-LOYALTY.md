# PLAN V4 — Lidl Plus und PAYBACK

Grundlage: `SPEC-V4-LOYALTY.md`  
Scope: direkte Provider-Synchronisierung; kein Mail-/PDF-/Dateiimport.

## Ziel

Providerneutrales Kundenkarten-Fundament, danach Lidl-Plus-Belegsync und – nur bei
erfülltem Machbarkeits-Gate – PAYBACK-Read-only-Sync. Jede Etappe ist separat
testbar und commitbar. Kein Live-Providercode vor rechtlicher und technischer
Freigabe.

## Geplante Dateien

### Backend

- `backend/loyalty_models.py` — Pydantic-Requests/Responses
- `backend/loyalty_access.py` — Mitglieder-/Sichtbarkeitsrechte
- `backend/loyalty_connections.py` — Verbindungen, Credential-Refs, Status
- `backend/loyalty_provider.py` — Ports, Capabilities, DTOs, Fehlerklassen
- `backend/loyalty_sync.py` — Locks, Cursor, Retry, Sync-Läufe
- `backend/loyalty_persistence.py` — idempotente Upserts
- `backend/receipt_normalize.py` — kanonischer Belegvertrag
- `backend/receipt_matching.py` — deterministischer Bankmatch
- `backend/loyalty_matching.py` — PAYBACK-Matches
- `backend/item_categories.py` — Artikelregeln und Split-Vorschläge
- `backend/providers/fake.py` — vollständiger Testprovider
- `backend/providers/lidl_plus.py` — gekapselter read-only Lidl-Adapter
- `backend/providers/payback.py` — nur nach bestandenem Gate
- `backend/routes_loyalty.py` — Verbindungs-, Sync- und Loyalty-Endpunkte
- `backend/routes_receipts.py` — Bon-/Match-/Artikel-Endpunkte
- `backend/__init__.py` — Router registrieren, Status aktualisieren

### Migrationen

- `migrations/004_loyalty_foundation.sql` — Verbindungen, Sync-Läufe, Balances,
  Aktivitäten, Verfall, Partner, Coupons
- `migrations/005_receipts.sql` — Belege, Positionen, Matches, Artikelregeln

### Frontend

- `frontend/LoyaltyView.tsx` — Kundenkartenübersicht
- `frontend/LoyaltyConnectionCard.tsx` — Status/Sync/Trennen
- `frontend/LoyaltyConnectDialog.tsx` — Provider-Opt-in und Login
- `frontend/LidlReceiptsView.tsx` — Bonliste
- `frontend/LidlReceiptDetail.tsx` — Artikel, Summen, Kategorien, Match
- `frontend/PaybackView.tsx` — Punkte, Verfall, Aktivitäten, Coupons
- `frontend/LoyaltySyncHistory.tsx` — redigierte Sync-Läufe
- `frontend/ExternalMatchReview.tsx` — Vorschläge/Bestätigung
- `frontend/loyaltyApi.ts` — API-Aufrufe
- `frontend/loyaltyTypes.ts` — UI-Typen
- `frontend/HaushaltsbuchPage.tsx` — Kundenkarten-Navigation

### Tests

- `tests/test_loyalty_connections.py`
- `tests/test_loyalty_sync.py`
- `tests/test_receipts.py`
- `tests/test_receipt_matching.py`
- `tests/test_loyalty_matching.py`
- `tests/test_lidl_provider.py`
- `tests/test_payback_provider.py` (nur nach Gate)
- `tests/test_loyalty_security.py`
- `tests/fixtures/loyalty/` — ausschließlich synthetisch/redigiert

## Implementierungsreihenfolge

### Phase 0: Freigaben und technische Spikes

#### Task 0.1 — Roadmap korrigieren

- [ ] Falsche PAYBACK-Referenz entfernen.
- [ ] Forschungsdokumente Lidl/PAYBACK verlinken.
- [ ] Live-Provider als experimentell/read-only markieren.
- [ ] Commit: `docs(haushaltsbuch): correct loyalty provider references`

#### Task 0.2 — Lidl-Live-Spike außerhalb des Produktpfads

- [ ] Separates deutsches Testkonto verwenden.
- [ ] Benutzergeführten PKCE-Login ohne Passwortübergabe verifizieren.
- [ ] `state`, `nonce`, Redirect und Tokenrotation dokumentieren.
- [ ] Ticketliste, Pagination und mindestens zehn strukturell unterschiedliche
      redigierbare Belege prüfen.
- [ ] Rabatte, Coupons, Pfand, Wiegeware, Retoure und Summenabweichung erfassen.
- [ ] 401/403/429, Rate-Limit und Schemaänderung prüfen.
- [ ] Keine CAPTCHA-/Attestation-/WAF-Umgehung.
- [ ] Gate: reproduzierbarer read-only Zugriff und dokumentierte Freigabe.
- [ ] Bei Gate-Fail: Lidl-Adapter bleibt deaktiviert; Fundament/Fake-Adapter dürfen
      trotzdem gebaut werden.

#### Task 0.3 — PAYBACK-Live-Spike außerhalb des Produktpfads

- [ ] Offiziellen Consumer-/Partnerzugang schriftlich anfragen/priorisieren.
- [ ] Falls zulässig: interaktiven Login und 2SV ohne Passwortpersistenz prüfen.
- [ ] Erneuerbare Sitzung, Punktestand, Verfall, Aktivitäten, Coupons, Partner,
      stabile IDs und Pagination verifizieren.
- [ ] App-Credential-Extraktion darf keine Dauerabhängigkeit sein.
- [ ] Keine Couponaktivierung oder Punkteeinlösung.
- [ ] Gate: zulässiger, erneuerbarer read-only Zugriff ohne Schutzumgehung.
- [ ] Bei Gate-Fail: kein Live-PAYBACK-Adapter; UI zeigt Provider nicht als
      verbindbar, Fundament/Fake-Adapter bleiben nutzbar.

### Phase 1: Providerneutrales Fundament

#### Task 1.1 — Migration 004 und Domainmodelle

- [ ] RED: Migrationstest für alle Loyalty-Tabellen, FKs, Uniques und Checks.
- [ ] Migration `004_loyalty_foundation.sql` schreiben.
- [ ] `loyalty_models.py`: Verbindung, Capabilities, Balance, Aktivität, Verfall,
      Partner, Coupon und Sync-Lauf.
- [ ] GREEN: Migration zweimal anwenden; Schema und Constraints prüfen.
- [ ] Commit: `feat(haushaltsbuch): add loyalty foundation schema`

#### Task 1.2 — Provider-Port und Fake-Adapter

- [ ] RED: Contracttests für alle Fähigkeiten und Fehlerklassen.
- [ ] Provider-DTOs/Port ohne Lidl-/PAYBACK-Details definieren.
- [ ] Fake-Adapter für vollständige, fehlende und fehlerhafte Capabilities.
- [ ] Tests: 401, 403, 429, 5xx, Timeout, SchemaChanged, Pagination.
- [ ] Commit: `feat(haushaltsbuch): add loyalty provider contract`

#### Task 1.3 — Verbindungen und Credential-Referenzen

- [ ] RED: Owner/Member/Outsider, mehrere Karten, Doppelverbindung, Revisionen.
- [ ] `loyalty_connections.py` und `loyalty_access.py` implementieren.
- [ ] Secrets über `hydrahive.credentials.store`; DB nur `credential_ref`.
- [ ] Tests beweisen: kein Secret in DB/API/Audit/Logs.
- [ ] Commit: `feat(haushaltsbuch): manage loyalty connections securely`

#### Task 1.4 — Sync-Engine

- [ ] RED: paralleler Sync, Crash vor Cursor, Wiederholung, Rate-Limit, Reauth.
- [ ] DB-Lock pro Verbindung, harte Request-/Seiten-/Zeitbudgets.
- [ ] Cursor erst nach erfolgreicher Seite; idempotente Upserts.
- [ ] Manueller Sync-Endpunkt und Sync-Verlauf.
- [ ] Commit: `feat(haushaltsbuch): add idempotent loyalty sync engine`

#### Task 1.5 — Kundenkarten-UI

- [ ] UI-Tests: leer, verbinden, aktiv, syncing, reauth, blocked, error.
- [ ] Übersicht, Verbindungskarten, Connect-/Disconnect-Dialog, Sync-Historie.
- [ ] Fähigkeiten-basierte Anzeige; experimentelle Warnung.
- [ ] Commit: `feat(haushaltsbuch): add loyalty connections UI`

### Phase 2: Kanonische Belege und Matching

#### Task 2.1 — Migration 005 und Belegvertrag

- [ ] RED: Beleg/Positionen/Adjustments/Matches/Regeln, FKs und Uniques.
- [ ] Migration `005_receipts.sql`.
- [ ] Normalizer mit Minor Units/Decimal, Locale, Zeitzone und Währung.
- [ ] Summenvalidierung, `needs_review`, keine Rohpayload-Dauerpersistenz.
- [ ] Commit: `feat(haushaltsbuch): add canonical receipt model`

#### Task 2.2 — Lidl-Bankmatching

- [ ] RED: eindeutiger Treffer, Gleichstand, Wochenendversatz, Barzahlung,
      falsche Währung, bereits bestätigter Match.
- [ ] Score/Gründe/Algorithmusversion implementieren.
- [ ] Vorschlag bestätigen, ablehnen, lösen; keine stille Ledger-Änderung.
- [ ] Commit: `feat(haushaltsbuch): match receipts to bank transactions`

#### Task 2.3 — Artikelkategorien und Split-Postings

- [ ] RED: GTIN-Regel, Namensregel, Historie, LLM-Fallback, Pfand/Rabatt.
- [ ] Artikelregeln und Kategorie-Vorschläge.
- [ ] Review-UI für Multi-Kategorie-Aufteilung.
- [ ] Atomare Split-Postings; Summe exakt gleich Transaktionsbetrag.
- [ ] Commit: `feat(haushaltsbuch): categorize receipt items and split bookings`

#### Task 2.4 — Bon-UI

- [ ] Bonliste, Bondetail, Warnungen, Positionen und Matchreview.
- [ ] Accessibility, Mobilansicht, große Bons mit 200+ Positionen.
- [ ] Commit: `feat(haushaltsbuch): add receipt review UI`

### Phase 3: Lidl Plus (nur nach Gate 0.2)

#### Task 3.1 — Interaktiver Login

- [ ] RED: State/Nonce/PKCE, Callback-Replay, falscher User, Timeout.
- [ ] Sichtbarer benutzergeführter Flow; keine automatische AGB-Annahme.
- [ ] Refresh-Token im Credential-Store, Access-Token nur im Speicher.
- [ ] Tokenrotation atomar; Reauth/Disconnect.
- [ ] Security-Audit vor Commit.
- [ ] Commit: `feat(haushaltsbuch): connect Lidl Plus securely`

#### Task 3.2 — Lidl-Ticketadapter

- [ ] RED mit redigierten/synthetischen List-/Detail-Fixtures.
- [ ] Host-Allowlist, Timeouts, Limits, Pagination, Fehlerabbildung.
- [ ] Ticketdetails normalisieren: Artikel, Rabatte, Coupons, Pfand, Retouren.
- [ ] Idempotenz und Inhaltsänderungen testen.
- [ ] Commit: `feat(haushaltsbuch): sync Lidl Plus receipts read-only`

#### Task 3.3 — Lidl-Pilot

- [ ] Feature-Flag standardmäßig aus; Kill-Switch testen.
- [ ] Manueller Sync; DE/de; keine parallelen Abrufe.
- [ ] Mehrwöchiger interner Pilot: keine Sperren, Duplikate, Betragsfehler.
- [ ] Datenschutz-/Security-Abnahme.
- [ ] Erst danach optional täglichen Sync mit Jitter planen.

### Phase 4: PAYBACK (nur nach Gate 0.3)

#### Task 4.1 — Interaktiver Login

- [ ] RED: 2SV erforderlich, sichere Gerätefreigabe, Sessionablauf, Reauth.
- [ ] Kein Passwort/Cookie als dauerhafter Zielzustand.
- [ ] Erneuerbare Sitzung im Credential-Store; Disconnect.
- [ ] Security-Audit vor Commit.
- [ ] Commit: `feat(haushaltsbuch): connect PAYBACK securely`

#### Task 4.2 — PAYBACK-Read-only-Adapter

- [ ] RED: Balance, Verfall, Aktivitäten, Coupons, Partner und Pagination.
- [ ] Capabilities dynamisch melden.
- [ ] Keine `activatecoupon`- oder Redeem-Methode implementieren.
- [ ] Idempotenz, Korrekturen, Remote-Gone und Fehlerfälle.
- [ ] Commit: `feat(haushaltsbuch): sync PAYBACK data read-only`

#### Task 4.3 — PAYBACK-Matching und UI

- [ ] RED: Partneralias, Datumsfenster, Mehrdeutigkeit, Einlösung/Storno.
- [ ] Match-Vorschläge zu Beleg/Buchung, keine Ledger-Betragsänderung.
- [ ] Punktestand, Verfall, Aktivitäten, Coupons, Partner, Matchreview.
- [ ] Commit: `feat(haushaltsbuch): add PAYBACK insights and matching`

#### Task 4.4 — PAYBACK-Pilot

- [ ] Feature-Flag aus; manueller Sync; minimaler Requestumfang.
- [ ] Mehrwöchiger interner Pilot und Kill-Switch-Test.
- [ ] Keine Sperren, Duplikate, Punktefehler oder PII-Leaks.
- [ ] Erst danach begrenzte Betaentscheidung.

### Phase 5: Abschluss

#### Task 5.1 — Security/Datenschutz

- [ ] Threat Model: Token-Diebstahl, SSRF, Callback-Replay, IDOR,
      Haushaltsleck, Provider-Payload, Log-Leak, Retry-Sturm.
- [ ] Security-Audit aller neuen Endpunkte und Adapter.
- [ ] Lösch-/Export-/Trennverhalten testen und dokumentieren.
- [ ] Keine Secrets/PII in Logs, Audit und Telemetrie.

#### Task 5.2 — Regression und Release

- [ ] Alle Haushaltsbuchtests, ruff, Typecheck und Build grün.
- [ ] Module-manifest-Version passend erhöhen; Featurestatus in `__init__.py` nur
      für tatsächlich freigegebene Provider auf `available` setzen.
- [ ] API-Contract und Changelog aktualisieren.
- [ ] `hh-review` und `verification-before-completion`.
- [ ] PR je abgeschlossener Phase, kein monolithischer Gesamt-PR.

## Release-Etappen

1. **V4.0 Foundation:** Verbindungen, Fake-Adapter, Sync-Engine, UI; keine Liveprovider.
2. **V4.1 Receipts:** Belegvertrag, Matching, Artikelkategorien.
3. **V4.2 Lidl Beta:** nur bei Lidl-Gate; read-only/manuell.
4. **V4.3 PAYBACK Beta:** nur bei PAYBACK-Gate; read-only/manuell.
5. **V4.4 Scheduled Sync:** nur nach stabilen Piloten; täglich mit Opt-in.

## Globale Akzeptanzkriterien

- [ ] Kein Mail-, PDF-, OCR- oder Dateiimport im Scope.
- [ ] Keine schreibenden Provideraktionen in V1.
- [ ] Keine Schutzumgehung oder Passwortpersistenz.
- [ ] Provider-Fail stoppt sicher und verändert kein Ledger.
- [ ] Wiederholung/Crash erzeugt keine Duplikate oder Cursorverlust.
- [ ] Haushalts-/Mitgliedsisolation und Secret-Schutz vollständig getestet.
- [ ] Beleg-/Punkte-Matches sind Vorschläge, begründet und reversibel.
- [ ] Provider können per Kill-Switch deaktiviert werden, ohne lokale Daten zu
      beschädigen.
