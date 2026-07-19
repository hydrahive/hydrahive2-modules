# Haushaltsbuch V4.2 – PAYBACK Browser-Bridge

## Was

Eine manuelle, ausschließlich lesende Browser-Bridge importiert die im angemeldeten PAYBACK-Webkonto sichtbaren Daten in das providerneutrale Loyalty-Modell des Haushaltsbuchs. Die PAYBACK-Anmeldung bleibt vollständig im Browser auf `payback.de`; HydraHive erhält weder Passwort noch Cookies, Session-/API-Tokens, private App-Secrets oder vollständiges HTML.

## Warum

PAYBACK bietet keinen öffentlichen Endnutzer-API-Zugang und keinen Self-Service-Datenexport. Für Einkaufsverhaltensanalysen werden dennoch die im Nutzerkonto sichtbaren Konto-, Punkte-, Partner- und Coupondaten benötigt. Eine vom Nutzer bewusst ausgelöste Browser-Bridge ist sicherer und transparenter als serverseitiges Scraping oder die reverse-engineerte mobile API.

## Umfang V1

Die Bridge erfasst, soweit auf der jeweils geöffneten PAYBACK-Seite sichtbar:

- aktuellen Punktestand und zeitlich versionierte Beobachtung;
- angekündigten Punkteverfall;
- Punkteaktivitäten mit Datum, Punkteänderung, Partner, Beschreibung und optionalem Einkaufsbetrag;
- Coupons mit Partner, Titel, Beschreibung, Gültigkeit, Status, Multiplikator, Bonuspunkten und Bedingungen;
- Partnerstammdaten, die aus Aktivitäten und Coupons abgeleitet werden.

Nicht verfügbare Felder werden nicht erfunden. Artikelpositionen werden nur unterstützt, wenn PAYBACK sie tatsächlich sichtbar bereitstellt; V1 verspricht keine Einzelartikel.

## Datenfluss

1. Ein angemeldeter HydraHive-Nutzer startet den PAYBACK-Browserimport.
2. Das Backend erzeugt kryptografisch zufällig einen Einmalcode mit zehn Minuten Laufzeit. Persistiert wird nur ein HMAC des Codes.
3. Die Browsererweiterung erfasst lokal nacheinander PAYBACK-Übersicht, Punktekonto und Couponseite. Eine Vorschau zeigt Anzahl und Art der erkannten Daten.
4. Nach bewusster Bestätigung sendet die Erweiterung ausschließlich den streng typisierten normalisierten Payload zusammen mit dem Einmalcode an HydraHive.
5. Das Backend verbraucht den Code atomar, erstellt oder aktualisiert genau eine PAYBACK-Browser-Bridge-Verbindung des Mitglieds und persistiert die Daten idempotent.
6. Das Haushaltsbuch zeigt Punktestand, Verfall, Aktivitäten, Partner, Coupons und einfache Einkaufsverhaltenskennzahlen an.

## API-Vertrag

### `POST /loyalty/payback/bridge/start`

Authentifiziert. Body:

```json
{
  "accepted_experimental_risk": true,
  "alias": "PAYBACK",
  "visibility": "owner"
}
```

Antwort:

```json
{
  "flow_id": "uuid",
  "pairing_code": "43+ zufällige Zeichen",
  "expires_at": "ISO-8601",
  "import_path": "/api/modules/haushaltsbuch/loyalty/payback/bridge/import"
}
```

### `GET /loyalty/payback/bridge/status/{flow_id}`

Authentifiziert und eigentümergebunden. Liefert `pending|consumed|expired` und nach Import optional die Verbindung.

### `GET /loyalty/payback/bridge/extension-package`

Authentifiziert. Liefert Dateiname, SHA-256 und Base64 eines reproduzierbar im Speicher erzeugten ZIPs der Manifest-V3-Erweiterung.

### `POST /loyalty/payback/bridge/import`

Nicht über HydraHive-JWT authentifiziert; ausschließlich durch den hochentropischen, kurzlebigen Einmalcode autorisiert. Der Code ist auf Haushalt/Mitglied/Flow gebunden und wird atomar genau einmal verbraucht.

Payload-Grenzen:

- max. 2.000 Aktivitäten;
- max. 1.000 Coupons;
- max. 100 Verfallspositionen;
- max. 500 Partner;
- Textfelder und IDs strikt begrenzt;
- keine unbekannten Felder;
- Datum, Geld, Punkte, Status und URLs strikt validiert;
- mindestens ein verwertbarer Datensatz;
- kein HTML-Feld und kein Cookie-/Token-Feld im Schema.

### `GET /loyalty/payback/connections/{connection_id}/data`

Authentifiziert und nach bestehender Haushalts-/Sichtbarkeitslogik geschützt. Liefert neuesten Punktestand, begrenzte Historie, Verfall, Aktivitäten, Coupons, Partner und aggregierte Einkaufskennzahlen.

## Browsererweiterung

- Manifest V3 für Chromium-basierte Browser als V1;
- feste Leseberechtigung nur für `https://www.payback.de/*`;
- optionale Hostberechtigung für die vom Nutzer eingegebene HydraHive-Origin;
- keine Cookie-Berechtigung, kein `webRequest`, keine TLS-Ausnahme;
- kein Nachladen externen Codes;
- keine Mutation, kein Klick auf Aktivierung/Einlösung;
- kurzlebige lokale Zwischenspeicherung nur des normalisierten Payloads und Pairingcodes;
- Daten werden nach erfolgreichem Import gelöscht;
- defensive, versionierte Selektoren und deduplizierte Heuristiken;
- unbekannte DOM-Versionen führen zu einer sichtbaren Warnung statt erfundener Daten.

## Persistenz

Die bestehenden Tabellen für `loyalty_balances`, `loyalty_expirations`, `loyalty_activities`, `loyalty_partners` und `loyalty_coupons` werden wiederverwendet. Aktivitäten erhalten optional `purchase_amount_minor` und `purchase_currency`. Eine neue Flow-Tabelle speichert ausschließlich HMAC, Ablauf, Eigentümerbindung, Metadaten und Verbrauchsstatus – niemals den Klartextcode oder PAYBACK-Sitzungsdaten.

## Sicherheitsanforderungen

- keine PAYBACK-Zugangsdaten, Cookies, Tokens oder App-Secrets;
- Einmalcode: mindestens 256 Bit Entropie, HMAC im Ruhezustand, zehn Minuten TTL, atomarer Einmalverbrauch;
- keine Secrets in Logs, Audit oder API-Fehlern;
- keine CORS-Freigabe für beliebige Webseiten; Cross-Origin-Zugriff erfolgt nur über explizite Extension-Hostpermission;
- Datenimport vollständig in einer DB-Transaktion;
- konstante, generische Fehlercodes am öffentlichen Importendpoint;
- Input-Limits vor teurer Verarbeitung;
- Sichtbarkeit und Verwaltung entsprechen bestehenden Haushaltsregeln.

## Akzeptanzkriterien

- Ein Nutzer kann das Extension-ZIP aus HydraHive laden und lokal als entpackte Erweiterung installieren.
- Übersicht, Punktekonto und Coupons lassen sich lokal erfassen und vor dem Versand prüfen.
- HydraHive empfängt keine PAYBACK-Authentisierungsdaten und persistiert kein Roh-HTML.
- Ein gültiger Code funktioniert genau einmal; abgelaufene, falsche und bereits verbrauchte Codes liefern denselben generischen Fehler.
- Fremde Haushaltsmitglieder können private Verbindungen und Daten nicht sehen oder importieren.
- Wiederholte Imports erzeugen keine doppelten Aktivitäten/Coupons/Partner.
- Einkaufsbeträge werden nur gespeichert, wenn sie sichtbar und eindeutig parsebar sind.
- Das Frontend zeigt Daten und Kennzahlen read-only an; es gibt keine Aktivierungs-/Einlöseaktion.
- Tests, Ruff und Frontend-Build sind grün.
