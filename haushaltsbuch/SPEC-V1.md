# Haushaltsbuch V1 — gemeinsamer Buchungskern

## Ziel

V1 ersetzt die Dummy-Seite durch ein lokal nutzbares Haushaltsbuch für genau einen gemeinsamen Haushalt pro HydraHive-Benutzer. Es enthält Mitglieder, Konten, Kategorien, einen intern doppelt geführten Buchungskern, hybride Budgets, einfache wiederkehrende Zahlungen, Prognose und Audit-Verlauf.

Bankimport, Beleg-OCR, Kundenkarten und KI-Kategorisierung folgen auf diesem Fundament in getrennten Etappen.

## Verbindliche Produktentscheidungen

- Jeder Benutzer kann genau einem Haushalt angehören.
- Haushaltsrechte referenzieren eine unveränderliche Core-`user_id`; der Benutzername dient nur als Anzeige- und Suchwert.
- V1 setzt einen rückwärtskompatiblen Core-Identitätsvertrag mit `user_id`, striktem Current-User-Lookup und Prüfung gelöschter/deaktivierter Benutzer voraus.
- Ein Haushalt hat einen Eigentümer und beliebig viele Mitglieder aus den vorhandenen HydraHive-Benutzern.
- Alle Mitglieder sehen alle Konten, Salden, Buchungen und Budgets.
- Alle Mitglieder dürfen sämtliche Finanzdaten erstellen und bearbeiten.
- Nur der Eigentümer darf Mitglieder verwalten, Eigentum übertragen und den Haushalt löschen.
- Alle Finanzänderungen werden auditierbar gespeichert.
- Die Oberfläche verwendet einfache Begriffe; intern gilt doppelte Buchführung.
- Der Haushalt besitzt eine Basiswährung, standardmäßig EUR.
- Geldbeträge werden als Integer in der kleinsten Währungseinheit gespeichert, nie als Float.

## Funktionsumfang

### Haushalt und Mitglieder

- Haushalt beim ersten Aufruf anlegen
- Name, Basiswährung und Haushaltszeitzone wählen
- Eigentümer kann einen vorhandenen HydraHive-Benutzer über den exakten Benutzernamen direkt hinzufügen; serverseitig wird dieser auf die stabile `user_id` aufgelöst
- alternativ einen zeitlich begrenzten Einladungscode erzeugen, den ein angemeldeter Benutzer selbst annimmt und damit seine stabile `user_id` verknüpft
- Einladungscode wird nur einmal im Klartext angezeigt; gespeichert wird ausschließlich sein Hash
- Einladung kann widerrufen werden, ist standardmäßig 24 Stunden gültig und einmal verwendbar
- Mitglieder entfernen und Eigentum an ein anderes Mitglied übertragen
- Benutzer darf nicht gleichzeitig Mitglied eines zweiten Haushalts sein
- letzter Eigentümer kann den Haushalt nur nach ausdrücklicher Bestätigung löschen

### Konten

Kontotypen:

- Girokonto
- Tages-/Sparkonto
- Bargeld
- Kreditkarte
- PayPal/Wallet
- Darlehen/Verbindlichkeit
- Wertkonto/Depot-Gesamtwert
- frei definierbar

Felder:

- Name, Typ, Kontoinhaber, Währung
- optional maskierte Bankkennung
- Anfangssaldo als eigener Eröffnungsvorgang
- berechneter Saldo
- aktiv oder archiviert
- Revision für konkurrierende Änderungen

### Kategorien

- Einnahme- und Ausgabekategorien
- Unterkategorien über `parent_id`
- Name, Icon, Farbe und Sortierung
- Kategorien werden archiviert statt hart gelöscht, sobald Buchungen existieren
- initiale Standardkategorien können beim Anlegen eines Haushalts erzeugt werden

### Buchungen

Die UI bietet:

- Einnahme
- Ausgabe
- Umbuchung
- Split-Buchung
- Rückerstattung
- Storno

Ein Vorgang enthält Kopf- und Posting-Daten. Die Summe aller Postings in Basiswährung muss exakt null sein. Ein Vorgang wird nur vollständig und atomar gespeichert.

Ledger-Invarianten:

- jeder Vorgang besitzt mindestens zwei Postings
- jedes Posting verweist exklusiv entweder auf ein Finanzkonto oder auf eine Kategorie
- Vorgang, Konten und Kategorien gehören zwingend demselben Haushalt
- Konto-Postings verwenden die Kontowährung als Originalwährung
- Kategorienpostings werden in Haushaltsbasiswährung geführt
- Storno und Ersatzvorgang laufen jeweils in einer atomaren DB-Transaktion
- DB-Constraints sichern die XOR- und Haushaltsgrenzen zusätzlich zur Servicevalidierung

Vorgangsdaten:

- Buchungs- und Valutadatum
- Empfänger/Absender
- Verwendungszweck und Notiz
- Status `posted` oder `reversed`
- Quelle `manual`, später `import`, `receipt`, `lidl_plus`, `payback`
- Ersteller, Zeitstempel und Revision

Posting-Daten:

- Finanzkonto oder Kategorie
- Originalbetrag und ISO-Währung
- Basisbetrag
- Wechselkurs als Decimal-String, nicht Float
- optionales Haushaltsmitglied als Kostenträger

Statt hartem Löschen erzeugt die Anwendung ein Storno mit Gegenpostings. Metadaten dürfen mit Revision/Audit korrigiert werden; finanzielle Werte werden bei einer Korrektur durch Storno und Ersatzvorgang geändert.

### Mehrwährungen

- Haushalt hat eine Basiswährung
- Konto hat genau eine Währung
- Fremdwährungsposting speichert Original- und Basisbetrag
- Wechselkurs, Kursdatum und Kursquelle werden gespeichert
- V1 erlaubt manuelle Kurse; automatische Kursquellen folgen später
- Rundungsdifferenzen werden über ein internes Rundungskonto ausgeglichen und sichtbar auditiert

### Budgets

Budgetarten:

- monatlich ohne Übertrag
- monatlich mit Restübertrag
- dauerhafte Rücklage
- einmaliger Zeitraum
- Jahresbudget

Budgets gelten für eine Kategorie oder als Haushaltsgesamtbudget. Sie speichern Betrag in Basiswährung, Zeitraum, Warnschwellen und Übertragsregel.

Budgetregeln:

- für denselben exakten Scope (eine Kategorie oder Haushaltsgesamtbudget) dürfen sich aktive Gültigkeitsintervalle nicht ganz oder teilweise überschneiden, unabhängig von der Budgetart
- Eltern- und Kindkategorie dürfen eigene Budgets besitzen; Kindbuchungen zählen im Elternbudget mit und die UI kennzeichnet die Überlappung
- Haushaltsgesamtbudget und Kategoriebudgets dürfen parallel bestehen und werden getrennt ausgewertet
- abgeschlossene Perioden erhalten unveränderliche Snapshots
- rückdatierte Buchungen erzeugen einen separat sichtbaren Perioden-Adjustmentsatz; der ursprüngliche Snapshot wird nicht überschrieben
- jede Budgetdefinition, Periodenschließung und Anpassung ist audit- und revisionspflichtig

### Wiederkehrende Zahlungen und Prognose

V1 unterstützt manuell angelegte Serien mit:

- Einnahme oder Ausgabe
- Kategorie und Quell-/Zielkonto
- Frequenz, nächster Fälligkeit und optionalem Enddatum
- erwartetem Betrag und Toleranz
- Vertragspartner, Kündigungsfrist und Notiz

Die Prognose zeigt bestätigte Serien für 30, 90 und 365 Tage. Automatische Serienerkennung und Preisabweichungsanalyse folgen später, das Datenmodell berücksichtigt aber bereits Status und Vertrauenswert.

Kalenderregeln:

- alle Fälligkeiten werden in der Haushaltszeitzone berechnet
- jede Monatsserie speichert einen unveränderlichen `anchor_day` von 1 bis 31
- ein `anchor_day` 29/30/31 wird in kürzeren Monaten nur für diese Fälligkeit auf den letzten Kalendertag geklemmt; der Anker selbst ändert sich nicht (31. Januar → 28./29. Februar → 31. März)
- Schaltjahre folgen dem gregorianischen Kalender
- verpasste Fälligkeiten werden als überfällig angezeigt, aber niemals automatisch als Finanzbuchung gebucht
- Prognosen werden deterministisch aus letzter bestätigter beziehungsweise nächster Fälligkeit erzeugt

### Übersicht

- Gesamtsaldo in Basiswährung
- Einnahmen und Ausgaben des aktuellen Monats
- Budgetverbrauch
- nächste wiederkehrende Zahlungen
- 30-/90-Tage-Prognose
- letzte Buchungen
- Warnungen bei prognostizierter Unterdeckung

### Audit und Parallelbearbeitung

Audit-Ereignisse speichern:

- Haushalt und Akteur
- Entität und Entitäts-ID
- Aktion
- vorherige und neue Werte als strukturierte Daten
- Zeitstempel

Alle änderbaren Entitäten — Haushalt, Mitgliedschaft, Einladung, Konto, Kategorie, Vorgang, Budget und Serie — besitzen eine Revision oder einen gleichwertigen atomaren Zustands-Guard. Ein Update, Storno oder Widerruf mit veraltetem Zustand liefert HTTP 409 statt fremde Änderungen still zu überschreiben. Jede Mutation in diesen Bereichen erzeugt ein Audit-Ereignis.

Die vollständige Haushaltslöschung ist die einzige bewusste Ausnahme von dauerhafter Audit-Aufbewahrung: Vor der doppelten Bestätigung wird ein Export inklusive Audit angeboten. Danach werden Haushalt, Finanzdaten, Anhänge und Audit-Ereignisse in einer atomaren Löschtransaktion vollständig entfernt. Die Oberfläche weist ausdrücklich darauf hin, dass danach auch die Historie nicht wiederherstellbar ist.

## Datenmodell

Vorgesehene Tabellen mit Präfix `module_haushaltsbuch_`:

- `households`
- `members`
- `invites`
- `accounts`
- `categories`
- `transactions`
- `postings`
- `budgets`
- `budget_periods`
- `budget_adjustments`
- `recurring_rules`
- `audit_events`

Die Tabellen werden per `ctx.register_migrations(...)` in der gemeinsamen HydraHive-Sessions-Datenbank angelegt und durch das Präfix logisch isoliert; es gibt keine separate Modul-Datenbank. Alle fachlichen Tabellen tragen `household_id`. Der Zugriff nutzt den strikten Core-Principal mit stabiler `user_id`, nicht nur den Benutzernamen.

## API-Bereiche

- `/household`
- `/household/members`
- `/household/invites`
- `/household/invites/accept`
- `/household/export`
- `/accounts`
- `/categories`
- `/transactions`
- `/transactions/{id}/reverse`
- `/budgets`
- `/recurring`
- `/forecast`
- `/dashboard`
- `/audit`

Autorisierungsmatrix:

- Haushalt anlegen: authentifizierter Benutzer ohne bestehenden Haushalt
- Einladung annehmen: authentifizierter Benutzer ohne bestehenden Haushalt plus gültiger Code
- Status des eigenen Haushalts lesen: Haushaltsmitglied
- Finanzdaten lesen/schreiben: Haushaltsmitglied
- direktes Hinzufügen, Einladungen, Entfernen und Eigentumsübertragung: Eigentümer
- Haushaltslöschung: Eigentümer mit expliziter Bestätigung

Alle unbekannten oder fremden Haushaltsressourcen antworten mit 404.

## Frontend-Struktur

Cockpit-Seite mit Bereichen:

1. Übersicht
2. Buchungen
3. Konten
4. Budgets
5. Wiederkehrend
6. Haushalt

Formulare verwenden gestapelte Cockpit-Dialoge. Destruktive Aktionen erfordern eine explizite Bestätigung. Salden und Budgetzustände werden nicht allein durch Farbe vermittelt.

## Sicherheit und Datenschutz

- lokale/offline nutzbare Kernfunktionen
- keine Bank-, Karten- oder LLM-Verbindungen in V1
- keine Finanz- oder Identitätsdaten in Logs
- Authentifizierung an jedem Endpoint; Haushaltsmitgliedschaft gemäß expliziter Autorisierungsmatrix
- owner-only für direktes Hinzufügen, Einladungen, Mitgliedschaft und Haushaltslöschung
- direkte Benutzerprüfung nur gegen exakten Namen; keine globale Benutzerliste für Haushaltsmitglieder
- Einladungstokens mit kryptografischem Zufall, gespeichert als Hash, einmalig und mit Ablaufzeit
- atomare Datenbanktransaktionen für Vorgang plus Postings
- Betrags- und Währungsvalidierung serverseitig
- Auditdaten sind nur für Haushaltsmitglieder sichtbar
- keine harte Löschung gebuchter Finanzvorgänge

## Akzeptanzkriterien

- Zwei Mitglieder desselben Haushalts sehen und bearbeiten dieselben Finanzdaten.
- Ein Benutzer kann keinem zweiten Haushalt hinzugefügt werden.
- Direktes Hinzufügen validiert einen exakten vorhandenen HydraHive-Benutzernamen, ohne eine Benutzerliste offenzulegen, und speichert dessen stabile `user_id`.
- Ein gelöschter/deaktivierter Benutzer sowie ein später unter gleichem Namen neu angelegter Benutzer erhält keine alten Haushaltsrechte.
- Einladungscodes sind gehasht, widerrufbar, zeitlich begrenzt und nur einmal verwendbar.
- Vor Haushaltslöschung kann der Eigentümer einen vollständigen JSON-Export einschließlich Audit abrufen.
- Bestätigte Haushaltslöschung entfernt Finanz- und Auditdaten vollständig und atomar.
- Nichtmitglieder erhalten für Haushaltsdaten 404 statt Datenexistenz zu verraten.
- Jeder gespeicherte Vorgang ist in Basiswährung exakt ausgeglichen.
- Einnahme, Ausgabe, Umbuchung, Split und Storno verändern Salden korrekt.
- Fremdwährungsbuchungen speichern Original- und Basiswerte ohne Float-Arithmetik.
- Alle Änderungen erzeugen Audit-Ereignisse.
- Veraltete Revisionen liefern HTTP 409.
- Alle fünf Budgetarten berechnen Soll/Ist und Übertrag korrekt.
- Bestätigte Serien erscheinen in 30-/90-/365-Tage-Prognosen.
- Backendtests, Frontend-Typecheck und Produktionsbuild sind grün.

## Nicht in V1

- CSV-, MT940- oder CAMT-Import
- Belegupload und OCR
- Lidl Plus und PAYBACK
- automatische Wechselkurse
- KI-Kategorisierung
- automatische Erkennung wiederkehrender Zahlungen
- FinTS, PSD2 oder schreibende Bankaktionen
