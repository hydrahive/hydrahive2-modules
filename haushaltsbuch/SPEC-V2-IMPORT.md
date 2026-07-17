# Haushaltsbuch Etappe 2 — Bankimport-Inbox

## Was

Etappe 2 ergänzt das lokale Haushaltsbuch um eine persistente Import-Inbox für manuell exportierte Bankumsätze. Unterstützt werden die vom Ziel-Banking angebotenen Formate:

1. XML CAMT V8 (`camt.053.001.08`) als bevorzugtes Format
2. XML CAMT V2 (`camt.053.001.02`)
3. Text MT940
4. CSV-CAMT V2, CSV-CAMT V8, CSV-MT940 und CSV mit Kategorien über konfigurierbare Spaltenzuordnungen

Ein Upload erzeugt niemals sofort Ledger-Buchungen. Er wird in ein gemeinsames Zwischenmodell normalisiert und als prüfbarer Entwurf gespeichert. Erst ein expliziter Abschluss übernimmt die ausgewählten Zeilen atomar in den vorhandenen doppischen Buchungskern.

## Warum

Bankexporte unterscheiden sich in Zeichensatz, Spaltennamen, XML-Version und Informationsgehalt. Direkte Buchung würde Parserfehler, falsche Zuordnungen und Duplikate unmittelbar in das Finanz-Ledger schreiben. Die Inbox trennt deshalb Parsing, Prüfung und finanzielle Übernahme und hält jeden Schritt nachvollziehbar.

## Verbindliche Produktentscheidungen

- Kernfunktionen bleiben lokal/offline; es gibt keine Bankverbindung und keinen externen Request.
- Originaldateien werden nach dem Request nicht dauerhaft gespeichert.
- Der Dateiname wird auf einen reinen Anzeigenamen reduziert; Dateipfade werden nie verwendet.
- Upload-Limit: 10 MiB; maximal 10.000 Datensätze pro Import.
- Jede Datei wird zunächst vollständig validiert und dann normalisiert.
- CAMT V2/V8 werden namespace-unabhängig, aber nur innerhalb des erwarteten `Document/BkToCstmrStmt`-Vertrags gelesen.
- DTD- und Entity-Deklarationen sind verboten.
- Geld wird als Integer in Minor Units verarbeitet; Decimal-Strings werden exakt konvertiert.
- Eine Importzeile erzeugt grundsätzlich einen Ledger-Vorgang mit Konto- und Kategorieposting.
- Zeilen ohne gewählte Kategorie dürfen nicht abgeschlossen werden.
- Währung muss der Zielkontowährung entsprechen. Automatische FX-Konvertierung ist nicht Teil von Etappe 2.
- Positive Beträge werden als Einnahme, negative als Ausgabe interpretiert.
- Originaldatei-Hash erkennt identische Uploads. Ein normalisierter Buchungsfingerprint erkennt wiederholte Umsätze auch über verschiedene Exportformate.
- Eindeutige Bankreferenzen (`AcctSvcrRef`, End-to-End-ID o. ä.) ergeben starke Fingerprints. Ohne stabile Referenz entsteht ein schwacher Fingerprint aus Konto, Datum, Betrag, Währung, Gegenpartei und Zweck.
- Starke Duplikate werden standardmäßig verworfen. Schwache Treffer werden sichtbar gewarnt und dürfen bewusst angenommen werden.
- Der Abschluss ist atomar: Entweder werden alle ausgewählten Zeilen gebucht oder keine.
- Importierte Buchungen werden nicht hart gelöscht. Ein Import-Storno erzeugt Gegenbuchungen für alle noch nicht stornierten Vorgänge des Imports.
- Alle Mutationen folgen Haushaltsmitgliedschaft, Audit und Revisionsschutz der V1.

## Normalisiertes Zwischenmodell

Jede Importzeile enthält mindestens:

- Quellzeilennummer beziehungsweise XML-Elementnummer
- Buchungsdatum
- optionales Valutadatum
- Betrag in Minor Units
- ISO-Währung
- Gegenpartei
- Verwendungszweck
- optionale maskierte Gegenkonto-Kennung
- optionale Bankreferenz
- optionalen Kategoriehinweis aus CSV
- Parserwarnungen und Validierungsfehler
- Fingerprint und Fingerprint-Stärke
- Bearbeitungsstatus
- gewählte Haushaltskategorie
- Revision

Vollständige IBAN/BIC werden nicht persistiert. Für die Anzeige wird höchstens eine maskierte Kennung mit den letzten vier Zeichen gespeichert.

## Importzustände

### Importpaket

- `draft`: geparst und in Prüfung
- `imported`: ausgewählte Zeilen atomar gebucht
- `reversed`: alle zugehörigen aktiven Buchungen storniert

### Importzeile

- `pending`: prüfbar, noch ohne Entscheidung
- `accepted`: für Abschluss ausgewählt
- `rejected`: bewusst verworfen
- `duplicate`: standardmäßig wegen starkem Duplikat ausgeschlossen
- `error`: nicht übernehmbar, bis Daten korrigiert wurden
- `imported`: Ledger-Vorgang erzeugt
- `reversed`: zugehöriger Vorgang storniert

## CSV-Profile

Ein CSV-Upload wird im Browser zunächst lokal eingelesen, um Header und Beispieldaten für die Zuordnung anzuzeigen. Beim Upload werden Datei, Zielkonto und Mapping gemeinsam gesendet.

Pflichtzuordnungen:

- Buchungsdatum
- Betrag oder Soll/Haben-Betragspaar

Optionale Zuordnungen:

- Valutadatum
- Währung
- Gegenpartei
- Verwendungszweck
- Bankreferenz
- Gegenkonto
- Kategoriehinweis

Profiloptionen:

- Name
- Trennzeichen (`;`, `,`, Tab)
- Zeichensatz (`utf-8`, `utf-8-sig`, `cp1252`, `iso-8859-1`)
- Dezimaltrennzeichen
- Datumsformat
- Spaltenmapping

Profile gehören zum Haushalt und können gespeichert, aktualisiert und gelöscht werden. Die gelieferten Bankvarianten werden nicht über fragile feste Spaltenpositionen erkannt, sondern über speicherbare Profile abgebildet.

## API

Alle Endpoints liegen unter `/api/modules/haushaltsbuch` und verlangen einen Haushalts-Principal.

- `GET /import-profiles`
- `POST /import-profiles`
- `PUT /import-profiles/{id}`
- `DELETE /import-profiles/{id}?revision=...`
- `POST /imports` — Multipart mit Datei, Zielkonto, Format und optionalem CSV-Mapping
- `GET /imports`
- `GET /imports/{id}`
- `PATCH /imports/{id}/rows/{row_id}` — Entscheidung, Kategorie und korrigierbare Metadaten
- `POST /imports/{id}/complete`
- `POST /imports/{id}/reverse`

Unbekannte oder haushaltsfremde Ressourcen antworten mit 404.

## Persistenz

Migration `002_bank_import.sql` ergänzt:

- `module_haushaltsbuch_import_profiles`
- `module_haushaltsbuch_import_batches`
- `module_haushaltsbuch_import_rows`

Originaldateien oder vollständige Bankkennungen werden nicht gespeichert. Importzeilen referenzieren nach Abschluss die erzeugten Ledger-Vorgänge.

## Frontend

Die Haushaltsbuch-Navigation erhält zwischen „Buchungen“ und „Konten & Kategorien“ den Bereich „Importe“.

### Neuer Import

1. Zielkonto wählen
2. Datei auswählen
3. Format automatisch erkennen oder manuell korrigieren
4. bei CSV Profil wählen oder Spalten zuordnen
5. Datei als Entwurf hochladen

### Inbox

- Zusammenfassung aus Anzahl, Summe, Zeitraum, Fehlern und Duplikaten
- Filter nach offen, akzeptiert, verworfen, Duplikat und Fehler
- Zeile zeigt Datum, Betrag, Gegenpartei, Zweck, Kategorie und Status
- Kategorie wählen sowie Datum, Gegenpartei und Zweck korrigieren
- einzelne oder alle gültigen Zeilen annehmen/verwerfen
- Abschlussdialog zeigt verbindlich die Zahl und Summe der zu buchenden Zeilen

### Historie

- Dateiname, Format, Zielkonto, Zeitraum und Status
- importierte/verwarfene/fehlerhafte Zeilen
- Detailansicht
- vollständiges Import-Storno nach Bestätigung

Status wird nie ausschließlich über Farbe vermittelt.

## Sicherheit

- Authentifizierung und Haushaltsisolation vor jeder Verarbeitung
- 10-MiB-Limit auch bei fehlendem oder falschem `Content-Length`
- nur erlaubte Formate und Zeichensätze
- kein Dateipfad aus dem Uploadnamen
- XML ohne DTD/Entities und ohne externe Auflösung
- Parserfehler ohne Rohinhalt oder interne Pfade in Responses
- CSV-Formeln werden nur als Text behandelt; es gibt keinen Tabellenexport in Etappe 2
- parameterisierte SQL-Abfragen
- vollständige IBAN/BIC weder im Audit noch in Logs
- Datei-Hash und sensible Referenzen werden nur haushaltsintern verwendet
- keine automatische Übernahme oder Kategorieentscheidung

## Akzeptanzkriterien

- CAMT V8 und V2 derselben fachlichen Buchung ergeben dasselbe Zwischenmodell.
- Text-MT940 wird mit Datum, Betrag, Gegenpartei, Zweck und Referenz normalisiert.
- Die vier angebotenen CSV-Varianten können über speicherbare Profile importiert werden.
- Ein Upload erzeugt keine Ledger-Buchung.
- Fehlerhafte Zeilen bleiben sichtbar und verhindern nicht die Prüfung gültiger Zeilen.
- Ein starker Duplikattreffer wird standardmäßig nicht übernommen.
- Ein schwacher Duplikattreffer kann nach sichtbarer Warnung bewusst angenommen werden.
- Der Abschluss erzeugt für alle akzeptierten Zeilen exakt ausgeglichene Ledger-Vorgänge und ist atomar.
- Ein Import-Storno erzeugt Gegenbuchungen und ist nicht doppelt möglich.
- Fremde Haushalte erhalten 404 für Importpakete, Profile und Zeilen.
- Zu große Dateien, Entity-XML und mehr als 10.000 Datensätze werden abgewiesen.
- Backendtests, Ruff, Frontend-Typecheck und Produktionsbuild sind grün.

## Nicht in Etappe 2

- FinTS, PSD2 oder automatische Banksynchronisation
- automatische Kategorien oder KI-Vorschläge
- automatische Wechselkurse
- Belegupload/OCR
- Importregeln und Split-Vorlagen
- Hintergrundjobs
- dauerhafte Speicherung von Originaldateien
