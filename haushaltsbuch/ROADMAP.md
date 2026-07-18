# Haushaltsbuch — Produkt-Roadmap

## Zielbild

Ein gemeinsames, lokal nutzbares Haushaltsbuch, das Finanzkonten, Budgets, Bankimporte, Belege und Kunden-/Punktekarten zusammenführt. Externe Integrationen sind optionale Adapter; der Buchungskern bleibt ohne externe Dienste vollständig verwendbar.

## Etappe 0 — Dummy ✅

- installierbares Modul `haushaltsbuch` Version 0.1.0
- Cockpit-Reiter und Platzhalterseite
- geplante Bereiche sichtbar
- authentifizierter Status-Endpunkt

PR #36, Modul-main `caacd12`.

## Voraussetzung — stabile HydraHive-Benutzeridentität

Vor Etappe 1 liefert ein separater Core-PR:

- unveränderliche `user_id` für bestehende und neue Benutzer
- rückwärtskompatible Migration der Benutzerkonfiguration
- strikten Auth-Principal, der gelöschte/deaktivierte Benutzer und alte Tokens abweist
- exakten serverseitigen Benutzer-Lookup ohne globale Benutzerliste

Haushaltsmitgliedschaften referenzieren ausschließlich `user_id`, nie den veränderbaren Benutzernamen.

## Etappe 1 — Gemeinsamer Buchungskern ✅

Siehe `SPEC-V1.md` und `PLAN-V1.md`.

- ein Haushalt pro Benutzer
- Eigentümer und Mitglieder
- direktes Hinzufügen über exakten Benutzernamen sowie sichere Einladungscodes
- alle Finanzdaten haushaltsweit sichtbar und bearbeitbar
- Konten und Kategorien
- doppelte Buchführung hinter einfacher UI
- Einnahmen, Ausgaben, Transfers, Splits, Rückerstattungen und Storno
- Basis- und Fremdwährungen
- Audit und Konflikterkennung
- hybride Budgets
- manuelle wiederkehrende Zahlungen
- Prognosen und Dashboard

## Etappe 2 — Bankimport-Inbox ✅

Implementiert in Modulversion 1.1.0. Verbindliche Details stehen in `SPEC-V2-IMPORT.md` und `PLAN-V2-IMPORT.md`.

### Gemeinsamer Importvertrag

Jeder Parser normalisiert auf dasselbe Zwischenmodell:

- Buchungs-/Valutadatum
- Originalbetrag und Währung
- Gegenpartei
- IBAN/BIC maskiert beziehungsweise geschützt
- Verwendungszweck
- Bankreferenzen
- Quellzeile/-element
- Parserwarnungen
- stabiler Fingerprint

### Formate

1. CSV mit Profilen und Spaltenzuordnung
2. MT940
3. CAMT.053

### Prüfbereich

- Datei und Zielkonto wählen
- Vorschau vor Speicherung
- Fehler pro Zeile
- Duplikate über Datei-Hash und Buchungsfingerprint
- Kategorie-/Regelvorschläge
- einzelne Zeilen annehmen, ändern oder verwerfen
- Import atomar abschließen
- Import als Ganzes stornieren
- Importhistorie und Audit

## Etappe 3 — Regeln und Automatisierung

### Deterministische Regeln

Bedingungen:

- Gegenpartei
- maskierte IBAN oder Bankreferenz
- Verwendungszweck
- Konto
- Betrag/Bereich
- Währung
- Wochentag
- Importquelle

Aktionen:

- Kategorie
- Split-Vorlage
- Kostenträger
- Tags
- wiederkehrende Zahlung zuordnen

Regeln besitzen Priorität, Testmodus und Trefferhistorie. Jede automatische Anwendung bleibt im Import-Prüfbereich sichtbar.

### Optionale KI-Vorschläge

- nur nach Opt-in
- lokale Modelle bevorzugt
- externe Modelle nur mit Redaction von Identifikatoren
- keine automatische Übernahme
- Vorschlag mit Begründung und Vertrauenswert
- bestätigten Vorschlag optional als feste Regel speichern

## Etappe 4 — Belege und OCR

### Stufe A: Anhänge

- PDF/JPEG/PNG hochladen
- Größen-, MIME- und Pfadprüfung
- Beleg einer Buchung zuordnen
- sichere lokale Speicherung und Backup

### Stufe B: Belegkopf

- Händler
- Datum
- Gesamtbetrag
- Steuer
- Zahlungsart
- Vorschau und manuelle Korrektur

### Stufe C: Artikelpositionen

- Artikeltext
- Menge und Einheit
- Einzel-/Gesamtpreis
- Rabatt und Coupon
- Pfand
- Warengruppe/Kategorie
- Zuordnung einzelner Positionen zu Budgetkategorien

OCR-Daten verwenden denselben Belegvertrag wie spätere digitale Lidl-Plus-Belege.

## Etappe 5 — Wiederkehrende Zahlungen und Verträge

- automatische Erkennung ähnlicher Serien
- Bestätigung vor Aktivierung
- erwarteter Betrag und Toleranz
- Preissteigerungen
- Vertragsende und Kündigungsfrist
- sichere, wahrscheinliche und optionale Prognoseposten
- Unterdeckungswarnungen für 30/90/365 Tage

## Etappe 6 — Kunden- und Punktekarten-Fundament

Vollständige Planung: `SPEC-V4-LOYALTY.md` und `PLAN-V4-LOYALTY.md`.

- mehrere Verbindungen desselben Anbieters für verschiedene Mitglieder
- Mitgliedsprivate Daten, optional explizit haushaltsweit freigegeben
- Credential-Referenz statt Secret im Modul
- Punktestand, Verlauf, Verfall, Coupons, Belege und Sync-Status
- generischer, fähigkeitenbasierter Provider-Adapter
- idempotente Sync-Engine, Sync-Historie, Reauth und Kill-Switch
- nachvollziehbare, reversible Matches zu Buchungen/Belegen

Diese Etappen verwenden ausschließlich direkte Provider-Synchronisierung. Mail-,
PDF- und Dateiimporte gehören nicht zum Lidl-/PAYBACK-Scope.

## Etappe 7 — Lidl Plus

Technische Vorprüfung: `research/LIDL-PLUS-INTEGRATION.md`.

- interaktiver, benutzergeführter Login; kein Passwort speichern
- digitale Kassenbons samt Artikelpositionen direkt synchronisieren
- Rabatte, Coupons, Pfand, Wiegeware und Retouren normalisieren
- Belege mit Bankbuchungen abgleichen und Match bestätigen lassen
- Artikel auf Haushaltsbuchkategorien aufteilen und Regeln lernen
- manueller Sync zuerst; geplanter Sync erst nach stabilem Pilot
- read-only, Feature-Flag und Kill-Switch

Live-Implementierung nur nach rechtlichem und technischem Gate. Kein CAPTCHA-,
MFA-, Attestation- oder Bot-Schutz-Bypass.

## Etappe 8 — PAYBACK

Technische Vorprüfung: `research/PAYBACK-INTEGRATION.md`.

Die frühere Referenz `dduarte.github.io/Payback/api.html` war fachlich falsch und
bezog sich nicht auf PAYBACK Deutschland. Der Live-Adapter benötigt einen neu
verifizierten, zulässigen Zugriffspfad.

- Punktestand und Punktehistorie direkt synchronisieren
- bald ablaufende Punkte
- Coupons und Partner read-only
- Punkteaktivität mit Buchung/Beleg verknüpfen
- Punktegegenwert und tatsächliche Ersparnis getrennt auswerten
- Synchronisationshistorie, Reauth, Feature-Flag und Kill-Switch
- keine Couponaktivierung oder Punkteeinlösung in V1

Live-Implementierung nur bei erneuerbarer Sitzung ohne Passwortpersistenz,
Schutzumgehung oder dauerhafte App-Credential-Extraktion.

## Etappe 9 — Auswertungen und Exporte

- Cashflow und Sparquote
- Fixkosten/variable Kosten
- Monats-/Jahresvergleich
- Budgetabweichungen
- Vermögensentwicklung
- Händler- und Artikelanalyse
- Coupon-/Punkte-Ersparnis
- CSV- und PDF-Export
- Jahresarchiv

## Etappe 10 — optionale Bank-Synchronisation

Nur nach gesondertem Research und Security-Audit:

- FinTS/HBCI oder geeigneter PSD2-Anbieter
- ausschließlich lesender Zugriff
- niemals Überweisungen oder Zahlungsfreigaben
- Credentials-Store, MFA und Token-Rotation
- expliziter manueller Sync plus optionaler Zeitplan
- vollständige Sync-/Fehlerhistorie

## Übergreifende Leitplanken

- Offline-first und lokale Kernfunktionen
- keine Secrets oder Roh-Bankdaten in Logs
- alle externen Integrationen austauschbare Adapter
- Imports und KI-Ergebnisse immer prüfbar
- keine Float-Arithmetik für Geld
- Storno statt harter Löschung gebuchter Vorgänge
- Audit für jede Finanzänderung
- Tests pro Parser, Ledger-Invariante und Berechtigungsgrenze
