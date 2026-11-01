# Modul „Netzwerk“ – Bauplan Etappe 1b: eigene Angaben eintragen

Stand 01.11.2026 · Task d2b126e4 · baut auf 0.1.0 (Etappe 1a, PR #336) auf. Allgemein für jeden Anschluss und
Anbieter, nicht für einen Einzelfall. Weiter nur lesend gegenüber den Geräten. Neu ist, was der Nutzer selbst einträgt.

## 1. Ziel

Alles, was zu einem Anschluss gehört und nicht aus einem Gerät kommt, lässt sich im Modul pflegen: Vertrag,
Störungsmeldungen samt Terminen, Ausfalltage, Notizen mit Belegen, offizielle Messungen und Ersatzgeräte. Das Modul
setzt diese Angaben mit den Messdaten aus 1a zusammen und rechnet daraus, was das Gesetz hergibt. Den Rechenweg zeigt
es immer mit an.

## 2. Rechtsgrundlagen (gelesen am 01.11.2026, im Modul als Quelle verlinkt)

**§ 58 TKG** (gesetze-im-internet.de/tkg_2021/__58.html):
- Abs. 2: Der Anbieter dokumentiert die Störungsmeldung und die vereinbarten Termine. Kann er die Störung nicht
  innerhalb eines Kalendertages beheben, muss er spätestens am Folgetag über die Maßnahmen und den voraussichtlichen
  Zeitpunkt der Behebung informieren.
- Abs. 3: Ist die Störung nicht innerhalb von zwei Kalendertagen nach Eingang der Meldung beseitigt, gibt es ab dem
  Folgetag für jeden Tag des **vollständigen Ausfalls** eine Entschädigung. Am 3. und 4. Tag 5 € oder 10 %, ab dem
  5. Tag 10 € oder 20 % des Monatsentgelts, je nachdem, was höher ist. Ausnahmen: selbst verschuldet, gesetzliche
  Maßnahmen, behördliche Anordnung, höhere Gewalt. Eine Minderung nach § 57 Abs. 4 wird angerechnet.
- Abs. 4: Für jeden vom Anbieter versäumten Kundendienst- oder Installationstermin 10 € oder 20 % des Monatsentgelts,
  je nachdem, was höher ist.

**Zählweise im Modul (Lesart, im Rechenweg sichtbar):** Der Tag der Meldung ist Tag 0. Tag 1 und Tag 2 sind die
Frist. Tag 3 und Tag 4 bringen je 5 €/10 %, ab Tag 5 je 10 €/20 %. Gezählt werden nur Tage, die als vollständiger
Ausfall bestätigt sind. Die Ausnahmen (z. B. höhere Gewalt) beurteilt das Modul nicht. Es zeigt einen Hinweis.

**Messung der Bundesnetzagentur, Festnetz** (bundesnetzagentur.de → Internetgeschwindigkeit, Allgemeinverfügung
Nr. 99/2021):
- 30 Messungen innerhalb von 14 Tagen nach Start, an 3 Kalendertagen mit mindestens einem Kalendertag Abstand,
  10 Messungen je Tag, mindestens 5 Minuten Abstand. Zwischen der 5. und 6. Messung eines Tages mindestens 3 Stunden.
- Abweichung liegt vor, wenn (a) an mindestens 2 von 3 Tagen nicht wenigstens einmal 90 % der maximalen
  Geschwindigkeit erreicht werden, oder (b) die normalerweise verfügbare Geschwindigkeit nicht in 90 % der Messungen
  erreicht wird, oder (c) an mindestens 2 von 3 Tagen wenigstens einmal die minimale Geschwindigkeit unterschritten
  wird. Es reicht eine Abweichung bei einem der drei Werte, im Down- oder Upload.
- Rechtlich gilt nur das Messprotokoll der Desktop-App. Das Modul prüft die eingetragenen Messungen nach denselben
  Regeln als Vorab-Einschätzung und hebt das deutlich hervor.
- Mobilfunk-Zugänge haben eigene Regeln (5 Messtage, Prozent nach Haushaltsdichte). Sie kommen nicht in 1b.

Überall im Modul steht: „Eigene Rechnung nach dem Gesetzestext, keine Rechtsberatung.“

## 3. Umfang

### 1b-1 (erster PR, 0.2.0)

**A Vertrag (ein Anschluss)**
- Anbieter, Kundennummer, Tarifname, Zugangsart (Kabel, DSL, Glasfaser, Mobilfunk, sonstige), Vertragsbeginn,
  Monatspreis.
- Geschwindigkeit laut Produktinformationsblatt, je Download und Upload: maximal, normalerweise, minimal (Mbit/s).
- Ersetzt die Tarif-Felder aus 0.1.0. Die Migration übernimmt vorhandene Werte als „maximal“. Die Übersicht vergleicht
  die Speedtests künftig mit allen drei Stufen: „unter Minimum“ wird rot, „unter normal“ gelb.

**B Ersatzgeräte**
- Bezeichnung (z. B. „Mobilfunk-Router vom Anbieter“), Anschlussart (USB/LAN/WLAN), von/bis, Notiz.
- Erscheinen als Zeitraum in den Störungen, damit klar ist, wann ein Ersatzweg da war.

**C Störungsmeldungen und Termine**
- Meldung: Datum und Uhrzeit, Weg (Hotline, Chat, App, Mail, Brief, vor Ort), Ticketnummer, Beschreibung, Antwort
  des Anbieters, behoben am (optional).
- Verlauf je Meldung: Einträge mit Zeit und Text (Rückruf, Info nach § 58 Abs. 2 erhalten ja/nein, Zusagen).
- Termine je Meldung: Datum/Zeitfenster, Art (Techniker, Installation), Status (vereinbart, erledigt, vom Anbieter
  versäumt, von mir abgesagt).
- Hinweis, wenn die Info-Pflicht nach § 58 Abs. 2 offen ist, also die Meldung älter als einen Tag, nicht behoben und
  kein Info-Eintrag vorhanden.

**D Ausfalltage**
- Tag, Art (Kabel bzw. Anschluss ganz aus, Internet ganz aus, eingeschränkt), Begründung.
- Bei jedem Tag zeigt das Modul, was gemessen wurde: Stunden ohne Kabel, Stunden ohne Internet, Ausfälle laut Dream
  Machine. Vorschlag „vollständiger Ausfall?“ ab 20 Stunden ohne Kabel. Bestätigen muss der Nutzer selbst.
  Nur bestätigte Tage zählen für die Entschädigung.

**E Entschädigung (§ 58 Abs. 3 + 4)**
- Je Meldung: Frist, Tage 3/4 und ab 5, nur bestätigte vollständige Ausfalltage bis „behoben am“ (oder heute),
  versäumte Termine. Jeweils mit Betrag (fester Betrag oder Prozent, je nachdem, was höher ist) und Rechenweg in
  Worten. Summe.
- Kein Monatspreis eingetragen: nur die Mindestbeträge, mit Hinweis.

### 1b-2 (zweiter PR, 0.3.0)

**F Notizen und Belege**
- Notiz mit Datum, Titel, Text, optional Link. Optional verknüpft mit einer Meldung oder einem Tag.
- Dateien anhängen: PDF, PNG, JPG, TXT, je höchstens 20 MB. Gespeichert unter
  `settings.data_dir/modules/network/files/`. Dateiname zufällig, Originalname nur als Anzeige. Typ wird am Inhalt
  geprüft (Magic Bytes), nicht nur an der Endung.
- Herunterladen nur mit `module.network`, mit `Content-Disposition: attachment`. Bilder als Vorschau.

**G Messungen der Bundesnetzagentur (Festnetz)**
- Messkampagne anlegen (Start), Messungen eintragen: Zeit, Download, Upload, Ping. Messprotokoll als Datei anhängen.
- Prüfung des Ablaufs: 30 Messungen, 3 Tage mit Abstand, 10 je Tag, 5 Minuten bzw. 3 Stunden Abstand, 14 Tage.
  Fehlendes wird angezeigt, z. B. „Tag 2: noch 4 Messungen, frühestens ab 18:20“.
- Vorab-Einschätzung der drei Kriterien (a)–(c) gegen den Vertrag aus A, je Download und Upload, mit Zahlen.
- Ein Import aus der Desktop-App kommt erst, wenn deren Exportformat an einer echten Datei geprüft ist.

## 4. Technik

- Migration `002_records.sql`: Tabellen `module_network_contract`, `_backup_devices`, `_tickets`, `_ticket_events`,
  `_appointments`, `_outage_days`, später `_notes`, `_files`, `_bnetza_campaigns`, `_bnetza_measurements`. IDs als
  zufällige Text-IDs, Zeiten als Unix-Sekunden, Tage als `YYYY-MM-DD` (deutsche Zeit wie in 1a). Alte Tarif-Spalten
  bleiben stehen (SQLite), werden aber nicht mehr gelesen.
- Eigene Dateien je Bereich (≤ 200 Zeilen): `contract_store`, `tickets_store`, `days_store`, `compensation` (reine
  Rechnung, ohne DB), `bnetza` (reine Prüfung), dazu je Bereich die Routen und Pydantic-Modelle mit Grenzen
  (Textlängen, Zahlen 0–100 000, Datum gültig).
- Rechte: lesen `module.network`, ändern `network.configure`. Löschen über einen eigenen Bestätigungsdialog.
- Neue Fehlercodes mit Text in Deutsch und Englisch (z. B. `network_not_found`, `network_date_invalid`,
  `network_file_type`, `network_file_too_large`).
- Oberfläche: neue Reiter „Anschluss“ (Vertrag + Ersatzgeräte), „Meldungen“ (Meldungen, Termine, Ausfalltage,
  Entschädigung), später „Belege“ und „Messungen“. Formulare in Karten, Liste plus Bearbeiten, Handy-tauglich.

## 5. Prüfung

- Rote Tests zuerst, besonders für `compensation` und `bnetza`. Grenzfälle:
  - Meldung um 23:59, Wechsel auf Winterzeit, Behebung am Tag 2, Lücken zwischen Ausfalltagen.
  - Prozent höher als der feste Betrag, kein Monatspreis.
  - Termin versäumt bzw. von mir abgesagt.
  - BNetzA: 9 statt 10 Messungen, Tage ohne Abstand, 15. Tag, 90-%-Grenze genau getroffen.
- Mutanten in Backend und Frontend, volle Reihe, hydratest, E2E in 4 Breiten über sichtbare Texte.
- Datei-Uploads: falscher Typ trotz passender Endung, zu groß, Pfad im Namen (`../`), Herunterladen ohne Recht.

## 6. Danach

3c Störungsbericht (Druckansicht aus allen Daten), Agenten-Werkzeuge (nur lesen), FRITZ!Box mit Anmeldung
(Kabelwerte, Ereignisprotokoll), Etappe 2 Verwaltung.
