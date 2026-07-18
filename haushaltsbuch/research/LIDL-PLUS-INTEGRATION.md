# Lidl-Plus-Integration — technische und rechtliche Voranalyse

**Status:** Research, keine Implementierungsfreigabe  
**Stichtag:** 2026-07-18  
**Bezug:** `ROADMAP.md`, Etappe 7  
**Scope:** Ausschließlich lesender Abruf digitaler Lidl-Plus-Kassenbons über einen optionalen Provider-Adapter. **Nicht im Scope sind E-Mail-, PDF- oder sonstige Dateiimporte**, OCR sowie das Aktivieren/Deaktivieren von Coupons.

## Kurzfazit

Eine Lidl-Plus-Anbindung ist technisch grundsätzlich möglich, aber derzeit **nicht produktionsreif freigegeben**. Es gibt keine dokumentierte öffentliche Lidl-API für diesen Zweck. Das PyPI-Paket `lidl-plus` 0.3.5 nutzt reverse-engineerte App-Endpunkte, ist seit 2024 praktisch ungewartet und weist bekannte Ausfälle bei Login, Token-Abruf und Belegdetail-Endpunkt auf. Ein aktiver Fork berichtet zwar von Reparaturen, bleibt aber ebenso inoffiziell.

Empfehlung:

1. Etappe 7 nur als **experimentellen, explizit aktivierten Read-only-Adapter** planen.
2. Vor Produktivcode Teilnahme-/Nutzungsbedingungen rechtlich prüfen und mit einem deutschen Testkonto einen zeitlich begrenzten technischen Spike durchführen.
3. Keine Zugangsdaten im Haushaltsbuch speichern; nur einen rotierbaren Credential-Verweis auf ein verschlüsselt gespeichertes Refresh-Token.
4. Kein CAPTCHA-/Bot-Schutz-Bypass, keine automatische Annahme neuer Rechtstexte und keine Coupon-Mutation.
5. Die Integration hinter einer Provider-Schnittstelle und einem Kill-Switch halten. Der Buchungs- und Belegkern muss ohne Lidl vollständig funktionieren.

## 1. Fakten und Unsicherheiten

| Aussage | Einstufung | Konsequenz |
|---|---|---|
| Lidl bewirbt in Deutschland den „Digitalen Kassenbon“ als Lidl-Plus-Funktion. | **Fakt**, offizielle Produktseite | Der fachliche Use Case existiert. |
| Eine öffentliche, dokumentierte und für Drittanbieter freigegebene Kassenbon-API wurde nicht gefunden. | **Unsicherheit mit starkem Negativindikator** | Keine Stabilitäts- oder Nutzungszusage; vor Umsetzung schriftliche/rechtliche Klärung. |
| `lidl-plus` ist inoffiziell und basiert laut eigener Dokumentation auf reverse-engineerten Requests. | **Fakt** | Hohe technische und rechtliche Abhängigkeit; niemals als offizielle SDK behandeln. |
| PyPI-Version 0.3.5 wurde am 2024-02-08 veröffentlicht; das Upstream-Repository wurde zuletzt am 2024-08-14 gepusht. | **Fakt** | Veraltet gegenüber späteren API-Änderungen. Abhängigkeit nicht ungeprüft übernehmen. |
| Das Paket steht unter MIT-Lizenz. | **Fakt** | Code darf lizenzkonform verwendet/verändert werden; das gewährt **keine** Rechte zur Nutzung der Lidl-Dienste. |
| Upstream-Issues dokumentieren 403 beim Auth-Endpunkt, gebrochenen Browser-Login und 500 beim Belegdetail. | **Fakt für die berichteten Zeitpunkte**, kein allgemeiner Verfügbarkeitsbeweis | Der Adapter braucht klare Fehlerklassen, Backoff und Deaktivierung statt Workarounds. |
| Ein aktiver Fork `yagueto/lidl-plus` meldet funktionierenden Login und Belegabruf ab August 2025 und wurde 2026 weiterentwickelt. | **Drittanbieterbehauptung**, nicht unabhängig verifiziert | Nur als Spike-Referenz; nicht blind vendorn oder als Stabilitätszusage werten. |
| Country-/Language-Werte und Antwortschemata können landes-, konto- und API-versionsabhängig sein. | **Unsicherheit** | Zunächst nur `DE/de` freigeben; Schema strikt, aber vorwärtskompatibel parsen. |
| Offizielle Rate Limits, Token-Lebensdauer, Sperrschwellen und Beleg-Aufbewahrungsdauer sind unbekannt. | **Unsicherheit** | Niedrige Abruffrequenz, kein aggressives Polling, keine Parallelstürme, Stop bei 401/403/429. |
| Ob automatisierter Zugriff nach aktuellen Lidl-Plus- und My-Lidl-Konto-Bedingungen zulässig ist, ist hier nicht abschließend geklärt. | **Offene Rechtsfrage** | Rechtliche Freigabe ist ein hartes Gate vor Pilot/Release. |

**Nicht behauptet:** Dass ein derzeit erreichbarer Endpunkt dauerhaft verfügbar, eine konkrete Token-Lebensdauer garantiert oder automatisierter Zugriff vertraglich erlaubt ist.

## 2. Quellen

### Primär- und Herstellerquellen

- Lidl-Plus-Produktseite (digitaler Kassenbon und Links zu aktuellen Rechtstexten):  
  https://www.lidl.de/c/lidl-plus/s10007388
- Lidl-Plus-Teilnahmebedingungen:  
  https://www.lidl.de/c/lidl-plus-teilnahmebedingungen/s10005289
- Lidl-Plus-Datenschutzhinweise:  
  https://www.lidl.de/c/lidl-plus-datenschutzhinweise/s10005247?hidebanner=true
- My-Lidl-Konto-Nutzungsbedingungen:  
  https://www.lidl.de/c/mylidlkonto-nutzungsbedingungen/s10007934
- My-Lidl-Konto-Datenschutzhinweise:  
  https://www.lidl.de/c/mylidlkonto-datenschutzhinweise/s10007933

Rechtstexte sind dynamisch und müssen zum Entscheidungszeitpunkt erneut gelesen, versioniert dokumentiert und gegebenenfalls juristisch bewertet werden. Diese Analyse ist keine Rechtsberatung.

### Inoffizielle technische Quellen

- PyPI-Projektseite: https://pypi.org/project/lidl-plus/
- Maschinenlesbare PyPI-Metadaten: https://pypi.org/pypi/lidl-plus/json
- Upstream-Repository: https://github.com/Andre0512/lidl-plus
- MIT-Lizenz: https://raw.githubusercontent.com/Andre0512/lidl-plus/main/LICENCE
- Commit-Historie: https://github.com/Andre0512/lidl-plus/commits/main
- Auth 403 / möglicher Bot-Schutz: https://github.com/Andre0512/lidl-plus/issues/16 und https://github.com/Andre0512/lidl-plus/issues/23
- Gebrochene Login-Automation: https://github.com/Andre0512/lidl-plus/issues/24
- Fehler am Belegdetail-Endpunkt: https://github.com/Andre0512/lidl-plus/issues/20
- API-v3-/HTML-Fallback-Diskussion: https://github.com/Andre0512/lidl-plus/pull/22
- Aktiver inoffizieller Fork: https://github.com/yagueto/lidl-plus
- Juni-2026-Referenz zu Tokenrotation und aktuellem Android-Ticketvertrag:
  https://github.com/callummacintyre-ctrl/lidl-plus-api-reference

## 3. Authentifizierung und Token

### Beobachteter inoffizieller Ablauf

`lidl-plus` 0.3.5 bildet einen nativen OIDC/OAuth-ähnlichen App-Flow nach:

- Authority: `https://accounts.lidl.com`
- Client-ID: `LidlPlusNativeClient`
- Authorization Code mit PKCE
- Redirect-Schema: `com.lidlplus.app://callback`
- Scopes laut Paket: `openid profile offline_access lpprofile lpapis`
- interaktiver Browser-Login, je nach Konto/Land mit Telefon oder E-Mail und 2FA
- Tausch des Authorization Codes gegen Access- und Refresh-Token
- Erneuerung des Access-Tokens über das Refresh-Token

Diese Werte sind reverse-engineerte Implementierungsdetails, **kein stabiler Vertrag**. Die alte Bibliothek automatisiert Webseiten über Selenium/Selenium Wire und kann aktualisierte Rechtstexte standardmäßig automatisch akzeptieren. Beides darf nicht unverändert in HydraHive übernommen werden.

### Verbindliches Zielverhalten

- Verbindung nur nach explizitem Opt-in durch ein berechtigtes Haushaltsmitglied.
- Interaktiver Login in einem sichtbaren, vom Benutzer kontrollierten Browser-Kontext; kein Headless-Login als Standard.
- Passwort und MFA-Code werden niemals persistiert, an den Haushaltsbuch-Server übermittelt oder geloggt.
- Neue/änderte Lidl-Rechtstexte werden **nie automatisch akzeptiert**. Der Flow stoppt und verweist auf den offiziellen Dialog.
- CAPTCHA, Device Attestation, TLS-Fingerprinting, WAF oder andere Anti-Bot-Maßnahmen werden nicht umgangen.
- Persistiert wird nur das Refresh-Token im zentralen verschlüsselten Credential-Store. Das Modul speichert ausschließlich `credential_ref`, Provider, Konto-Alias, Land/Sprache und Status.
- Access-Token nur kurzlebig im Speicher; keine Tokens in URLs, Exceptions, Auditdetails, Telemetrie oder Test-Snapshots.
- Bei Refresh-Token-Rotation atomar zuerst neues Secret speichern, dann alte Version verwerfen.
- „Trennen“ widerruft das Token, falls ein unterstützter Revocation-Endpunkt verifiziert ist; andernfalls lokales Secret sicher löschen und den Benutzer auf Passwort-/Kontosicherheitsoptionen bei Lidl hinweisen.
- Nur eine Ablehnung am Tokenendpoint (`invalid_grant`/400/401) setzt `reauth_required`. Ein Ticket-401 wird genau einmal nach Refresh wiederholt und bei erneuter Ablehnung als statischer Stage-Fehler gespeichert; 403 setzt `blocked`. Keine Login-Schleife.

### Offene Auth-Fragen für den Spike

- Funktioniert ein benutzergeführter PKCE-Flow ohne Request-Interception und ohne Passwortübergabe an HydraHive?
- Gibt es einen verifizierbaren State-/Nonce-Schutz und wie wird der App-Redirect sicher abgefangen?
- Rotiert das Refresh-Token bei jeder Verwendung und werden alte Tokens sofort ungültig?
- Welche Laufzeiten besitzen Access- und Refresh-Token tatsächlich?
- Welche MFA-Varianten gelten für deutsche Konten; tritt CAPTCHA oder Device Binding auf?
- Existiert ein offizieller Revocation-/Logout-Endpunkt?

## 4. Daten und Normalisierung

### Beobachtete Daten

Die alte Bibliothek bietet eine paginierte Ticketliste und einen Abruf pro Ticket-ID. Das dokumentierte Artikelbeispiel enthält unter anderem:

- `name`
- `quantity`, `isWeight`
- `currentUnitPrice`, `originalAmount`
- `taxGroup`, `taxGroupName`
- `codeInput` (beispielsweise EAN/GTIN)
- `discounts[]` mit Beschreibung und Betrag
- `deposit`
- `giftSerialNumber`

Das vollständige aktuelle DE-Schema wurde nicht mit einem realen Konto verifiziert. Insbesondere Händler-/Filialdaten, Zeitstempel, Währung, Zahlart, Summen, Retouren, negative Positionen, Rundungen und Mehrwertsteuer-Summen bleiben Spike-Gegenstand.

### Kanonischer Belegvertrag

Der Lidl-Adapter normalisiert in denselben Belegvertrag wie die geplante Beleg-/OCR-Etappe; Providerfelder dürfen nicht in Ledger- oder UI-Code durchsickern:

**Belegkopf**

- interne `receipt_id`
- `household_id`, `connection_id`, Besitzer-Mitglied
- `source = "lidl_plus"`
- `provider_receipt_id` und gehashter, haushaltsgebundener Fingerprint
- Händler normalisiert auf Lidl; Originalbezeichnung separat
- Filial-ID/-Name/-Adresse nur soweit geliefert und fachlich benötigt
- Kaufzeitpunkt mit Original-Zeitzone beziehungsweise explizitem „Zeitzone unbekannt“
- Gesamtbetrag als Minor Units oder `Decimal`, niemals `float`
- ISO-4217-Währung; keine stillschweigende EUR-Annahme bei fehlendem Feld
- Steueraufschlüsselung, Zahlungsart und Status nur wenn geliefert
- Summen für Rabatt, Coupon und Pfand
- `provider_updated_at`, `first_seen_at`, `last_seen_at`, Payload-Schema-Version

**Positionen**

- stabile interne Positions-ID und Provider-Reihenfolge
- Originaltext plus optional normalisierter Artikelname
- GTIN/EAN nur wenn plausibel validiert; keine Produktidentität aus Freitext erfinden
- Menge und Einheit getrennt; Dezimalwerte lokalunabhängig parsen
- Einzel-, Brutto-/Gesamtpreis in Minor Units/`Decimal`
- Positionsrabatte/Coupons als eigene Adjustments mit Vorzeichen und Bezug
- Pfand als eigenes Adjustment beziehungsweise eigene Position, nicht als Ware kategorisieren
- Steuergruppe/-satz nur bei eindeutiger Quelle
- Storno/Retoure/negative Positionen explizit modellieren
- Parserwarnungen und Konsistenzstatus

### Validierungsregeln

- Locale-Zahlen wie `"2,19"` deterministisch parsen; keine `float`-Zwischenwerte.
- `sum(position totals) + adjustments` gegen Beleggesamtbetrag prüfen. Abweichung nur mit dokumentierter Rundungs-/Pfandregel zulassen und als Warnung speichern.
- Unbekannte Felder ignorierbar, fehlende Pflichtfelder führen in `needs_review`, nicht zu erfundenen Defaults.
- HTML-Antworten niemals als JSON akzeptieren. Ein HTML-Fallback wäre ein eigener, standardmäßig deaktivierter Parser mit Sanitizing und separater Freigabe; für MVP nicht empfohlen.
- Rohpayloads standardmäßig nicht dauerhaft speichern. Für Diagnose nur nach Opt-in, verschlüsselt, stark befristet und redigiert; niemals Tokens/Header mit ablegen.

## 5. Adapterarchitektur

Empfohlene Grenze:

```text
Haushaltsbuch-Domain
  -> ReceiptSyncService
     -> LidlPlusProvider (Port/Interface)
        -> verifizierter HTTP-Client oder gekapselte Fork-Implementierung
```

Minimaler Read-only-Vertrag:

```text
connect_interactive(connection, callback) -> ConnectionStatus
probe(connection) -> ProviderCapabilities
list_receipts(connection, cursor, page_size) -> ReceiptPage
get_receipt(connection, provider_receipt_id) -> ProviderReceipt
refresh_auth(connection) -> TokenMetadata
revoke_or_disconnect(connection) -> DisconnectResult
```

Anforderungen:

- keine direkten `requests`-Aufrufe aus Routes oder Domain-Services;
- feste Connect-/Read-Timeouts, begrenzte Antwortgröße und TLS-Verifikation immer aktiv;
- Host-Allowlist für verifizierte Lidl-Hosts, Redirect-Allowlist und keine vom Provider frei gelieferten Abruf-URLs;
- explizite Fehlerklassen: `AuthRequired`, `ForbiddenOrBlocked`, `RateLimited`, `ProviderUnavailable`, `SchemaChanged`, `ReceiptGone`, `InvalidProviderData`;
- Abhängigkeit auf konkrete Paket-/Commit-Version pinnen und SBOM/Lizenzhinweis führen;
- wenn Fremdcode verwendet wird, nur hinter eigenem Interface, nach Security-Review und möglichst ohne Selenium Wire;
- Feature-Flag/Kill-Switch pro Installation und Verbindung;
- ausschließlich Read-only. Coupon-Aktivierung, Profiländerung und andere schreibende Providerfunktionen sind nicht Teil des Adapters.

## 6. Synchronisation

### Ablauf

1. Benutzer startet manuellen Sync oder aktiviert nach erfolgreichem Pilot einen zurückhaltenden Zeitplan.
2. Pro Verbindung genau einen verteilten/DB-basierten Lock erwerben.
3. Access-Token bei Bedarf einmal erneuern.
4. Ticketliste vollständig, sequentiell und mit begrenzter Seitengröße lesen.
5. Neue IDs und bekannte IDs innerhalb eines Überlappungsfensters detailliert abrufen.
6. Payload normalisieren und validieren.
7. Pro Beleg idempotent upserten; fachliche Änderungen versionieren und auditieren.
8. Matching-Vorschläge berechnen, aber nicht stillschweigend buchen oder Bankbuchungen verändern.
9. Cursor/Watermark erst nach erfolgreicher Verarbeitung der betroffenen Seite fortschreiben.
10. Sync-Lauf mit Zählern, Dauer und redigierten Fehlern abschließen.

### Idempotenz und Cursor

- Primärschlüssel: `(connection_id, provider_receipt_id)`.
- Zusätzlich kanonischer Inhalts-Hash zur Erkennung geänderter Details.
- Da Änderungszeitstempel und Sortiergarantie unklar sind: bei jedem Lauf neue Seiten plus konfiguriertes Überlappungsfenster erneut prüfen.
- Erster Sync begrenzt den historischen Zeitraum beziehungsweise die maximale Belegzahl und zeigt den Umfang vorab an.
- Ein entfernter Providerbeleg wird nicht lokal hart gelöscht. Erst nach mehreren vollständigen Läufen als `remote_unavailable` markieren; Ledger-/Auditdaten bleiben erhalten.
- Teilfehler dürfen erfolgreiche Belege nicht duplizieren. Ein Schemafehler stoppt den betroffenen Beleg oder bei breitem Auftreten den Lauf.

### Frequenz und Lastschutz

- MVP: ausschließlich manueller Sync.
- Später höchstens zurückhaltender Zeitplan, beispielsweise einmal täglich, mit Jitter und explizitem Opt-in.
- Keine parallelen Detailabrufe im MVP; später nur sehr kleine, begrenzte Parallelität nach Messung.
- Exponentieller Backoff mit Jitter bei 429/5xx und Beachtung von `Retry-After`.
- Bei 401 einmal Refresh; bei erneutem 401 stoppen. Bei 403 sofort stoppen. Keine automatische Wiederholung von Login/MFA.
- Keine unendlichen Pagination-, Refresh- oder Retry-Schleifen; harte Request-/Laufbudgets.

### Sync-Historie

Speichern: Verbindung, Start/Ende, Trigger `manual|scheduled`, Status, gelistete/neue/geänderte/übersprungene/fehlerhafte Belege, Cursor vorher/nachher, normalisierte Fehlerklasse und nächster erlaubter Versuch. Nicht speichern: Tokens, Passwort, MFA-Code, vollständige Header, rohe Antworten oder vollständige Einkaufslisten im technischen Log.

## 7. Matching mit Bankbuchungen

Matching erzeugt nur Vorschläge. Eine automatische Verknüpfung ist frühestens nach empirischer Kalibrierung zulässig und muss rückgängig gemacht werden können.

### Kandidatenbildung

- nur Ausgaben in derselben Währung;
- Betragsgleichheit auf Minor-Unit-Ebene als starkes Signal;
- Buchungs-/Valutadatum in einem konservativen Fenster um den Kaufzeitpunkt, zunächst `-1/+3` Kalendertage;
- normalisierte Gegenpartei enthält Lidl-Alias, aber Händlertext allein genügt nicht;
- bereits eindeutig mit anderem Beleg verknüpfte Buchungen ausschließen;
- bei Barzahlung keinen Bankmatch vorschlagen, sofern die Zahlungsart zuverlässig geliefert wird.

### Deterministische Bewertung

Beispiel, im Spike zu kalibrieren:

- exakter Betrag: +60
- gleiche Währung: Pflichtbedingung
- Datum 0/1/2/3 Tage entfernt: +25/+20/+12/+5
- starker Lidl-Merchant-Alias: +15
- passende Karten-/Zahlungsreferenz, falls datensparsam verfügbar: +20
- widersprechende Zahlungsart: Ausschluss

Nur bei eindeutig bestem Kandidaten und Mindestscore einen Vorschlag anzeigen. Abstand zum zweitbesten Kandidaten muss ausreichend groß sein. Mehrere Lidl-Einkäufe mit gleichem Betrag/Tag bleiben `ambiguous` und erfordern manuelle Auswahl. Gründe, Score, Algorithmusversion sowie Bestätigung/Ablehnung werden gespeichert. Ein Beleg kann höchstens einer Bankbuchung zugeordnet sein; eine Buchung kann bei Sammelzahlungen mehrere Belege benötigen, was im MVP manuell bleibt.

## 8. Datenschutz und Sicherheit

- **Datenminimierung:** Nur Belegdaten abrufen, nicht Coupons, Profil, Standortverlauf oder sonstige Kontodaten.
- **Zweckbindung:** Haushaltsbuch, Belegansicht und optionales Buchungsmatching; keine Werbung, Profilbildung oder Weitergabe.
- **Transparenz:** Vor Verbindung Kategorien, Zweck, Abruffrequenz, Speicherdauer, Haushalts-Sichtbarkeit und Widerruf erklären.
- **Haushaltsgrenze:** Verbindung gehört zunächst dem verbindenden Mitglied. Vor einer haushaltsweiten Freigabe muss dieses ausdrücklich bestätigen, dass alle Mitglieder Artikelkäufe sehen dürfen. Rollen/Berechtigungen serverseitig prüfen.
- **Secrets:** Refresh-Token verschlüsselt im zentralen Credential-Store; Datenbank enthält nur Referenz. Secret-Zugriff nach Least Privilege und auditierbar.
- **Logs/Telemetry:** Keine Einkaufspositionen, Filialadresse, Kontoidentifikatoren oder Secrets. Externe Telemetrie standardmäßig aus.
- **Lokale Speicherung:** Belegdaten in derselben geschützten lokalen Datenhaltung und im selben Backup-/Löschkonzept wie Finanzdaten.
- **Löschen/Trennen:** Verbindung und nicht mehr benötigte Providerkopien löschbar; gebuchte Finanzvorgänge/Audit folgen den Haushaltsbuch-Aufbewahrungsregeln. Auswirkungen vor Bestätigung anzeigen.
- **Betroffenenrechte/Export:** Herkunft `lidl_plus`, Zeitpunkte und Zuordnungen nachvollziehbar machen; rechtliche Rollen und Rechtsgrundlage hängen vom Betriebsmodell ab und müssen vor Release bewertet werden.
- **DPIA-Prüfung:** Vor breiter oder gehosteter Nutzung prüfen, ob Umfang, Haushaltsfreigabe und detaillierte Konsumprofile eine Datenschutz-Folgenabschätzung oder zusätzliche Maßnahmen erfordern.
- **Supply Chain:** Fremdbibliothek, Browser-/Driver-Downloads und transitive Abhängigkeiten prüfen. Laufzeit-Downloads von Webdrivern sind im Serverbetrieb abzulehnen.

## 9. Teststrategie

### Unit- und Vertragstests ohne Livekonto

- synthetische, redigierte JSON-Fixtures für Listen- und Detailantworten;
- Locale-Zahlen, Dezimalmengen, Gewicht, Unicode, Nullwerte und unbekannte Felder;
- Coupons/Rabatte auf Position und Belegebene, Pfand, Steuergruppen, negative Positionen, Retouren und Rundungsdifferenzen;
- fehlende Pflichtfelder, falsche Typen, übergroße Antworten und HTML statt JSON;
- Pagination: leere Seite, exakte Seitengrenze, Duplikate, wechselnde Gesamtzahl und Endlosschleifenschutz;
- Token-Rotation, `invalid_grant`, 401 nach Refresh, 403, 429 mit `Retry-After`, 5xx, Timeout und Verbindungsabbruch;
- Idempotenz bei Wiederholung, Crash zwischen Upsert und Cursor, geänderter Beleginhalt und remote verschwundener Beleg;
- Money-Invarianten ohne Float und Summenabgleich;
- Matching: eindeutiger Treffer, Gleichstand, gleicher Betrag mehrfach, Wochenendverschiebung, Barzahlung, falsche Währung und bereits verknüpfte Buchung;
- Berechtigungsgrenzen zwischen Haushalten/Mitgliedern und keine Secret-/PII-Leaks in Logs/Fehlern.

### Integrations- und Live-Smoke-Tests

- HTTP-Adapter gegen lokalen Fake-Provider; keine echten Lidl-Endpunkte in CI.
- Live-Smoke nur manuell, opt-in, mit separatem Testkonto, niedriger Requestzahl und dokumentierter Freigabe.
- Testsecrets ausschließlich im Credential-Store/CI-Secret, niemals als Fixture oder Environment-Dump.
- Erwartete Prüfung: interaktiver Login, Token-Rotation, zwei Listenseiten, Detailabruf, Wiederholung ohne Duplikat, Disconnect.
- Schema-Snapshots vollständig redigieren und nur dann dauerhaft übernehmen, wenn sie keine realen Einkaufs-/Kontodaten enthalten.

**Explizit ausgeschlossen:** Tests für E-Mail-, PDF- oder Dateiimport; diese Integration nimmt ausschließlich Providerantworten über den Adapter entgegen.

## 10. Phasen und Gates

### Phase 0 — Recht und Produktgrenze

- aktuelle Lidl-Plus- und My-Lidl-Konto-Bedingungen prüfen;
- zulässigen automatisierten, ausschließlich lesenden Zugriff und Verantwortlichkeiten bewerten;
- Datenschutzhinweis, Einwilligungs-/Aktivierungsdialog und Löschkonzept entwerfen.

**Gate:** schriftlich dokumentierte Freigabe. Ohne Freigabe kein Live-Spike mit automatisiertem Zugriff.

### Phase 1 — Technischer Spike, nicht produktiv

- DE/de-Testkonto;
- benutzergeführter PKCE-Login ohne Passwortpersistenz und ohne Bot-Schutz-Bypass;
- List-/Detail-Endpunkt, Pagination, Token-Rotation, Rate-Limit-Verhalten und aktuelles Schema erfassen;
- maximal wenige kontrollierte Abrufe; keine Coupon-Mutation.

**Gate:** Login und mindestens zehn unterschiedlich strukturierte, redigierbar dokumentierte Belege funktionieren reproduzierbar; keine 403-/CAPTCHA-Umgehung nötig.

### Phase 2 — Kanonischer Belegvertrag und Fake-Adapter

- Belegmodell aus Etappe 4 finalisieren;
- Provider-Port, Normalizer, Validierung, Sync-Status und synthetische Fixtures implementieren;
- Matching nur als deterministischer Vorschlag.

**Gate:** Unit-/Vertragstests, Ledger-/Money-Invarianten, Berechtigungs- und Security-Review bestanden.

### Phase 3 — Experimenteller manueller Read-only-Adapter

- Feature-Flag, Credential-Referenz, manueller Sync, Historie und Kill-Switch;
- nur DE/de, keine geplanten Jobs, kein automatisches Matching;
- kleine interne Pilotgruppe mit klarer Fehler-/Abschaltkommunikation.

**Gate:** mehrere Wochen ohne Sperren, Datenverlust, Duplikate oder breite Schemafehler; Datenschutz- und Security-Abnahme.

### Phase 4 — Begrenzte Freigabe

- optionaler täglicher Sync erst nach belastbaren Messdaten;
- Monitoring ausschließlich mit redigierten Metriken;
- dokumentierter Update-/Abschaltprozess bei Provideränderungen.

**Gate:** definierte SLOs und Wartungsverantwortung; weiterhin Beta/inoffiziell kennzeichnen.

## 11. Stop-Kriterien

Entwicklung oder Betrieb wird sofort gestoppt beziehungsweise der Adapter per Kill-Switch deaktiviert, wenn eines der folgenden Kriterien eintritt:

- rechtliche Prüfung ergibt ein Verbot oder unvertretbares Vertrags-/Sperrrisiko;
- Login erfordert CAPTCHA-, Attestation-, TLS-Fingerprint-, WAF- oder anderen Schutz-Bypass;
- Passwörter/MFA-Codes müssten serverseitig gespeichert oder automatisiert eingegeben werden;
- neue Rechtstexte könnten nur durch automatische Annahme passiert werden;
- wiederholte 403, Account-Sperre/-Warnung oder Hinweise auf Missbrauchserkennung;
- kein stabiler read-only Belegabruf ohne private App-Manipulation erreichbar ist;
- Schemaänderungen erzeugen falsche Beträge, verlorene Positionen oder nicht erklärbare Summendifferenzen;
- Token oder Einkaufsdaten gelangen in Logs, Telemetrie, Fehlerberichte oder ungeschützte Backups;
- Rate Limits bleiben unbekannt und ein sicherer, niedriger Abrufrhythmus kann nicht belegt werden;
- die Abhängigkeit ist ungepatcht verwundbar oder benötigt unkontrollierte Browser-/Driver-Downloads;
- Provideränderungen verursachen eine nicht begrenzbare Retry-/Login-Schleife;
- eindeutige Trennung von Haushalten oder Mitgliedsberechtigungen ist nicht gewährleistet;
- es gibt keine benannte Wartungsverantwortung für die inoffizielle Integration.

### Degradationsregel

Ein Ausfall von Lidl Plus darf niemals den Buchungskern, Bankimport, manuelle Belege oder bestehende Buchungs-/Belegzuordnungen blockieren. Bei Providerproblemen bleibt der letzte validierte lokale Stand lesbar, wird als veraltet markiert und nur durch einen expliziten späteren Sync aktualisiert. Es erfolgt kein stilles Löschen und keine automatische Änderung gebuchter Finanzdaten.
