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
- `POST /imports` ist Multipart mit `file`, `account_id`, `format=auto|camt|mt940|csv`, optional `mapping` als JSON und optional `profile_id`. CSV-Datumswerte im deutschen Punktformat akzeptieren pro Zelle sowohl zwei- als auch vierstellige Jahreszahlen.
- `GET /imports` liefert Paketzusammenfassungen; `GET /imports/{id}` zusätzlich normalisierte Zeilen.
- `DELETE /imports/{id}?revision=n&rows_revision=n` löscht ausschließlich unveränderte, noch nicht gebuchte Entwürfe samt Zeilen; gebuchte Historie bleibt unveränderlich.
- `PATCH /imports/{id}/rows/{row_id}` ändert Entscheidung, Kategorie und korrigierbare Metadaten mit `revision`.
- `POST /imports/{id}/complete` mit `{revision}` bucht alle akzeptierten Zeilen atomar.
- `POST /imports/{id}/reverse` mit `{revision}` storniert das gesamte Paket über Gegenbuchungen.
- Uploads erzeugen ausschließlich Entwürfe. Fehlerzeilen bleiben sichtbar, starke Duplikate sind standardmäßig ausgeschlossen.

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
- Passwort und MFA-Code werden ausschließlich direkt bei Lidl eingegeben. `POST /loyalty/lidl/auth/complete` erhält nur `{flow_token,callback_url,alias?,visibility}`. Die Callback-URL muss exakt dem gestarteten, höchstens zehn Minuten alten `com.lidlplus.app://callback`-Flow entsprechen.
- Das Refresh-Token liegt ausschließlich AES-GCM-verschlüsselt im zentralen Credential-Store. Access-Tokens bleiben nur für die Dauer eines Syncs im Arbeitsspeicher.
- `GET /loyalty/receipts` listet maximal 500 sichtbare, normalisierte Belege; `GET /loyalty/receipts/{id}` ergänzt Artikel und Adjustments. Rohpayloads und HTML-Belege werden nicht persistiert.
- Lidl-Sync ist manuell, read-only und auf DE/de sowie maximal 200 Belege pro Lauf begrenzt. PAYBACK bleibt weiterhin deaktiviert.
- Die Schnittstelle ist inoffiziell und experimentell. Es gibt keine Stabilitäts- oder Zulässigkeitszusage; CAPTCHA, WAF, Device Attestation und Rechtstextdialoge werden nicht automatisiert oder umgangen.

Create/Update-Payloads und Responses sind in `types.ts` beziehungsweise `loyaltyTypes.ts` vollständig typisiert. Die Clients stehen in `api.ts` und `loyaltyApi.ts`.
