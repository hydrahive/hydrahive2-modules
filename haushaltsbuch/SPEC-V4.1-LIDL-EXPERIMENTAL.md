# Spec V4.1: Experimenteller Lidl-Plus-Testconnector

## Was

HydraHive kann ein deutsches Lidl-Plus-Konto read-only über einen benutzergeführten
Authorization-Code-PKCE-Flow verbinden und digitale Kassenbons samt Artikeln manuell
synchronisieren. Die Integration ist ausdrücklich inoffiziell und experimentell.

## Warum

Der Haushalt soll die technische Machbarkeit mit einem realen Konto prüfen können,
ohne Passwort oder MFA-Code an HydraHive zu übermitteln und ohne Selenium,
Login-Automation oder Umgehung von Schutzmaßnahmen.

## Gewählter Ansatz

### Authentifizierung

1. Ein berechtigtes Haushaltsmitglied bestätigt den experimentellen Charakter und
   startet `POST /loyalty/lidl/auth/start`.
2. Das Backend erzeugt State, Nonce und S256-PKCE. Es gibt eine feste
   `accounts.lidl.com`-Authorize-URL sowie einen kurzlebigen, AES-GCM-verschlüsselten
   Flow-Token zurück.
3. Der Benutzer öffnet die URL in seinem eigenen Browser und meldet sich direkt bei
   Lidl an. HydraHive sieht weder Passwort noch MFA-Code.
4. Beim Redirect auf `com.lidlplus.app://callback?...` kopiert der Benutzer die
   vollständige Callback-URL in HydraHive.
5. `POST /loyalty/lidl/auth/complete` validiert Flow-Ablauf, Haushalt/Mitglied,
   Callback-Schema/-Host, State und Code. Der Code wird genau einmal gegen den festen
   Lidl-Token-Endpunkt getauscht.
6. Nur das Refresh-Token wird als Bearer-Credential im zentralen AES-GCM-Store
   gespeichert. Die Modul-DB enthält nur die Credential-Referenz und den
   haushaltsgebundenen Kontofingerprint.

Neue/aktualisierte Lidl-Rechtstexte werden nicht automatisch akzeptiert. CAPTCHA,
WAF, Device Attestation und vergleichbare Maßnahmen werden nicht umgangen. Scheitert
der manuelle Browserflow daran, stoppt der Test mit einer redigierten Meldung.

### Read-only HTTP-Client

- feste Hosts: `accounts.lidl.com`, `tickets.lidlplus.com`, optional
  `profile.lidlplus.com`; keine usergesteuerten URLs;
- ausschließlich `DE/de`;
- standardmäßig aktiver Testconnector mit optionalem Betreiber-Not-Aus `HH_HAUSHALTSBUCH_LIDL_ENABLED=0`;
- TLS-Verifikation, feste Timeouts, begrenzte Antwortgröße und sequentielle Abrufe;
- Tokenrefresh bei Bedarf, Rotation atomar im Credential-Store;
- 401 → `reauth_required`, 403 → `blocked`, 429 → Cooldown, 5xx → unavailable;
- keine Couponaktivierung, Profiländerung, Punkteeinlösung oder andere Writes.

### Belegvertrag

Migration 005 ergänzt:

- `loyalty_receipts`: Provider-ID/Fingerprint, Händler/Filiale, Kaufzeitpunkt,
  Gesamtbetrag, Währung, Rabattsumme, Inhalts-Hash, Validierungsstatus und Warnungen;
- `loyalty_receipt_items`: Reihenfolge, Originalname, GTIN, Menge/Einheit,
  Einzel-/Gesamtpreis, Steuergruppe und Retourenstatus;
- `loyalty_receipt_adjustments`: Rabatt, Coupon, Pfand oder Rundung mit optionalem
  Positionsbezug;
- `loyalty_auth_flows`: nur gehashte Flow-ID, Scope, Ablauf und Einmalverbrauch;
  niemals Code, Verifier oder Token.

Geld wird als Minor Units über `Decimal`, nie über `float`, normalisiert. Fehlende
oder widersprüchliche Felder führen zu `needs_review` und Warnungen statt erfundenen
Werten. Rohpayload und HTML-Beleg werden nicht persistiert.

### Synchronisation

Der vorhandene manuelle Sync-Lock wird erweitert:

1. Ticketliste begrenzt und paginiert laden.
2. Details neuer und bekannter Tickets sequentiell lesen.
3. Normalisieren und per `(connection_id, provider_receipt_id)` idempotent upserten.
4. Positionen/Adjustments bei geändertem Inhalts-Hash atomar ersetzen.
5. Zähler und redigierte Fehler im vorhandenen Sync-Lauf speichern.

### Oberfläche

- Lidl-Karte bietet „Experimentell verbinden“.
- Dialog erklärt Inoffizialität, read-only Umfang und Risiken; explizite Checkbox.
- Drei Schritte: Login-Link öffnen, Callback-URL einfügen, Verbindung abschließen.
- Verbindungsstatus und manueller Sync nutzen die bestehende Kundenkartenansicht.
- Liste synchronisierter Belege mit Detailansicht für Artikel, Rabatt und Pfand.

## Akzeptanzkriterien

- Passwort und MFA-Code passieren HydraHive weder im Request noch in Logs/DB/Vault.
- Callback wird nur für exaktes Custom-Schema, State und nicht verbrauchten Flow
  akzeptiert; Ablauf höchstens 10 Minuten.
- Refresh-Token liegt nur verschlüsselt im zentralen Credential-Store.
- Ein wiederholter Sync dupliziert keine Belege oder Artikel.
- Deutsches Lidl-Beispielschema mit Locale-Beträgen wird korrekt normalisiert.
- 401/403/429/5xx und Schemaabweichungen werden redigiert und sicher behandelt.
- Der Benutzer kann verbundene Lidl-Belege und Artikel lesen.
- Alle bestehenden Tests, Typecheck und Produktionsbuild bleiben grün.

### Ergänzung: initialer Access-Token-Handoff

Der Authorization-Code-Austausch liefert Access- und Refresh-Token. Das frisch
ausgestellte Access-Token wird bis zu seinem Ablauf ausschließlich im Arbeitsspeicher
an genau die neu erstellte Verbindung des registrierten Lidl-Adapters übergeben.
`probe()` verwendet ein noch nicht abgelaufenes Access-Token direkt und ruft den
Refresh-Endpunkt erst auf, wenn kein nutzbares In-Memory-Token vorhanden ist.

- Access-Tokens werden weder in Modul-DB noch Credential-Store persistiert.
- Tokenwert und Ablaufzeit werden vor dem Handoff strikt validiert.
- Wiederholte Syncs innerhalb der Tokenlaufzeit verwenden dasselbe Access-Token.
- Beim Trennen der Verbindung wird das In-Memory-Token sofort entfernt.
- Der erste Sync nach dem Login darf vor dem Ticketabruf keinen Refresh auslösen.
- Fehlt der In-Memory-Handoff, bleibt der bestehende sichere Refreshpfad erhalten.

## Nicht enthalten

- automatisierter/headless Login oder Selenium;
- automatische Annahme von Rechtstexten;
- CAPTCHA-/WAF-/Attestation-Umgehung;
- Couponaktivierung oder andere schreibende Lidl-Aktionen;
- automatischer Zeitplan, OCR/PDF/E-Mail-Import;
- stilles Ändern von Ledger-Buchungen;
- Stabilitäts- oder Zulässigkeitszusage für die inoffizielle Lidl-Schnittstelle.
