# Plan: Haushaltsbuch V1

## Ziel

Die Dummy-Seite wird zu einem praktisch nutzbaren gemeinsamen Haushaltsbuch mit Mitgliedern, Konten, Kategorien, Buchungen, Budgets, wiederkehrenden Zahlungen, Prognose und Audit-Verlauf.

## Geplante Dateien

### Core-Voraussetzung (separater Core-PR)

- `core/src/hydrahive/api/middleware/users.py` — unveränderliche `user_id` und exakter Lookup
- `core/src/hydrahive/api/middleware/auth.py` — strikter Principal mit aktueller Benutzerprüfung
- `core/tests/test_user_identity.py` — Migration, Löschung/Neuanlage und Token-Prüfung

### Backend

- `migrations/001_household_core.sql` — Tabellen, Indizes und Constraints
- `backend/__init__.py` — Router registrieren
- `backend/models.py` — Pydantic-Ein-/Ausgabemodelle
- `backend/access.py` — Haushalt aus Auth-Kontext und owner-only Guard
- `backend/households.py` — Haushalt, Mitglieder, Konten und Kategorien
- `backend/ledger.py` — Vorgänge, Postings, Salden und Storno
- `backend/budgets.py` — Budgetperioden und Überträge
- `backend/recurring.py` — Serien und Prognose
- `backend/audit.py` — strukturierte Audit-Ereignisse in den präfixierten Tabellen der gemeinsamen Sessions-DB
- `backend/routes_household.py` — Haushalt/Konten/Kategorien
- `backend/routes_ledger.py` — Buchungs-API
- `backend/routes_planning.py` — Budgets, Serien, Prognose, Dashboard

### Tests

- `tests/conftest.py` — isolierte Testdatei für die gemeinsam genutzte Sessions-DB, Benutzer und Auth
- `tests/test_households.py` — Ein-Haushalt-Regel und Rechte
- `tests/test_household_invites.py` — direktes Hinzufügen und sichere Einladungscodes
- `tests/test_accounts_categories.py` — Konten-/Kategorie-Lebenszyklus
- `tests/test_ledger.py` — Ledger-Invarianten und Salden
- `tests/test_ledger_fx.py` — Fremdwährung und Rundung
- `tests/test_audit_conflicts.py` — Audit und Revision 409
- `tests/test_budgets.py` — alle Budgetarten
- `tests/test_recurring.py` — Serien und Prognosen
- `tests/test_routes.py` — Auth, 404-Isolation und API-Verträge

### Frontend

- `frontend/index.tsx` — bestehende Route/Nav/i18n erweitern
- `frontend/api.ts` — typisierte REST-Aufrufe
- `frontend/types.ts` — Frontend-Verträge
- `frontend/HaushaltsbuchPage.tsx` — Cockpit-Shell und Bereichsnavigation
- `frontend/HouseholdSetup.tsx` — ersten Haushalt anlegen
- `frontend/DashboardView.tsx` — Monatswerte und Prognose
- `frontend/TransactionsView.tsx` — Liste, Filter und Storno
- `frontend/TransactionDialog.tsx` — Einnahme/Ausgabe/Umbuchung/Split
- `frontend/AccountsView.tsx` — Konten und Kategorien
- `frontend/BudgetsView.tsx` — hybride Budgets
- `frontend/RecurringView.tsx` — Serien und Prognose
- `frontend/HouseholdView.tsx` — Mitglieder und Eigentum

Jede Produktionsdatei bleibt möglichst unter 200 Zeilen; bei Überschreitung wird vor dem Commit weiter aufgeteilt.

## Implementierungsreihenfolge

### Task 0: Stabiler Core-Benutzerbezug (separater Core-PR)

- [ ] RED: bestehende Benutzer erhalten rückwärtskompatibel eine unveränderliche `user_id`
- [ ] RED: gelöschter Benutzer bleibt trotz altem JWT gesperrt
- [ ] RED: neu angelegter Benutzer mit gleichem Namen erhält eine andere `user_id`
- [ ] RED: exakter Lookup liefert nur Identität des angefragten Namens, keine Benutzerliste
- [ ] strikten Auth-Principal mit `user_id`, Username und Rolle implementieren
- [ ] bestehende `require_auth`-Konsumenten rückwärtskompatibel halten
- [ ] GREEN: Core-Auth-/User-Tests vollständig grün
- [ ] Security-Audit und eigener Core-PR
- [ ] Commit: `feat(auth): stabile Benutzeridentitäten bereitstellen`

### Task 1: Migration und isolierte Testumgebung

- [ ] RED: Test erwartet alle Tabellen/Indizes und scheitert ohne Migration
- [ ] `001_household_core.sql` mit Foreign Keys, Unique-, XOR- und Revision-Feldern erstellen
- [ ] `ctx.register_migrations(...)` in `backend/__init__.py` registrieren
- [ ] Starttest beweist, dass der Core die Migration in der gemeinsamen Sessions-DB ausführt
- [ ] Test-Fixtures mit zwei logisch isolierten Haushalten und mehreren stabilen Core-`user_id`s bauen
- [ ] Migration zweimal ausführen und Idempotenz prüfen
- [ ] GREEN: Migrationstests bestehen
- [ ] Commit: `feat(haushaltsbuch): V1-Datenmodell anlegen`

### Task 2: Haushalt und Mitgliedschaft

- [ ] RED: Benutzer-`user_id` kann nur einem Haushalt angehören
- [ ] RED: Haushalt anlegen und Einladung annehmen benötigen Auth, aber noch keine Mitgliedschaft
- [ ] RED: alle übrigen fremden Ressourcen liefern 404
- [ ] RED: nur Eigentümer verwaltet Mitglieder, Einladungen und Eigentumsübertragung
- [ ] RED: direktes Hinzufügen akzeptiert nur einen exakt vorhandenen Benutzernamen und legt keine Benutzerliste offen
- [ ] RED: Einladungstoken wird gehasht, läuft nach 24 Stunden ab, ist widerrufbar und einmalig
- [ ] RED: owner-only JSON-Export enthält Finanz- und Auditdaten vor der Löschung
- [ ] RED: doppelt bestätigte Haushaltslöschung purgt Haushalt, Finanz- und Auditdaten atomar
- [ ] `access.py`, Haushalt-Service und Routen implementieren
- [ ] gleichzeitige Mitgliedschaft durch DB-Constraint absichern
- [ ] kryptografisch zufällige Einladungen und atomare Annahme implementieren
- [ ] Revisions-/Zustands-Guard für Mitgliedschaft, Einladung, Widerruf und Eigentumsübertragung anwenden
- [ ] GREEN: Haushalts-/Einladungs-/Rechtetests bestehen
- [ ] Commit: `feat(haushaltsbuch): gemeinsamen Haushalt verwalten`

### Task 3: Konten und Kategorien

- [ ] RED: Mitglieder können gemeinsame Konten/Kategorien CRUD verwenden
- [ ] RED: archivierte Entitäten bleiben für historische Buchungen auflösbar
- [ ] Kontotypen, Währungen, Kontoinhaber und Kategoriebaum implementieren
- [ ] Standardkategorien beim Haushalts-Setup erzeugen
- [ ] Revision bei Updates verlangen; veraltet ergibt 409
- [ ] GREEN: Konten-/Kategorietests bestehen
- [ ] Commit: `feat(haushaltsbuch): Konten und Kategorien hinzufügen`

### Task 4: Ledger-Kern

- [ ] RED: Vorgang braucht mindestens zwei exakt ausgeglichene Postings
- [ ] RED: jedes Posting erfüllt Konto-XOR-Kategorie
- [ ] RED: Vorgang, Konten und Kategorien dürfen keine Haushaltsgrenze überschreiten
- [ ] RED: Einnahme, Ausgabe, Umbuchung und Split erzeugen korrekte Postings
- [ ] RED: Speichern ist atomar
- [ ] `ledger.py` mit Integer-Minor-Units und Basisbeträgen implementieren
- [ ] Salden aus Postings berechnen, nicht als veränderlichen Cache behandeln
- [ ] GREEN: Ledger-Tests bestehen
- [ ] Commit: `feat(haushaltsbuch): ausgeglichenen Buchungskern implementieren`

### Task 5: Fremdwährung und Storno

- [ ] RED: Original- und Basisbetrag bleiben reproduzierbar
- [ ] RED: Decimal-Kurs und Rundung erzeugen exakt ausgeglichene Basispostings
- [ ] RED: Storno erzeugt Gegenpostings, verlangt die aktuelle Revision und kann nicht doppelt erfolgen
- [ ] FX-/Rundungslogik und Reversal-Service implementieren
- [ ] keine Float-Werte im API-/DB-Pfad zulassen
- [ ] GREEN: FX- und Stornotests bestehen
- [ ] Commit: `feat(haushaltsbuch): Fremdwährung und Storno ergänzen`

### Task 6: Audit und Konflikte

- [ ] RED: jede Mutation an Haushalt, Mitgliedschaft, Einladung, Konto, Kategorie, Vorgang, Budget und Serie erzeugt ein Audit-Ereignis
- [ ] RED: Audit enthält stabile Akteur-`user_id`, Aktion und strukturierte Vorher-/Nachher-Daten
- [ ] RED: veraltete Revision beziehungsweise Zustandsversion liefert 409
- [ ] Audit-Service in alle schreibenden Services integrieren
- [ ] sensible Inhalte nicht loggen; Audit liegt geschützt in präfixierten Tabellen der gemeinsamen Sessions-DB
- [ ] GREEN: Audit-/Konflikttests bestehen
- [ ] Commit: `feat(haushaltsbuch): Audit und Revisionsschutz hinzufügen`

### Task 7: Hybride Budgets

- [ ] RED: Monatsreset, Restübertrag, Rücklage, Zeitraum und Jahresbudget
- [ ] RED: aktive Budgets desselben exakten Scopes dürfen sich auch teilweise nicht überschneiden
- [ ] RED: Kindbuchungen rollen nachvollziehbar in Elternbudgets; Gesamtbudget bleibt getrennt
- [ ] RED: abgeschlossene Periodensnapshots ändern sich nicht still; Rückdatierungen erzeugen Adjustments
- [ ] RED: Warnschwellen und Soll/Ist werden korrekt berechnet
- [ ] RED: Budgetupdates und Periodenschließungen verlangen aktuelle Revision
- [ ] Budget-Service und API implementieren
- [ ] Budgetwerte ausschließlich in Haushaltsbasiswährung führen
- [ ] GREEN: Budgettests bestehen
- [ ] Commit: `feat(haushaltsbuch): hybride Budgets implementieren`

### Task 8: Wiederkehrende Zahlungen und Prognose

- [ ] RED: Frequenzen erzeugen in der Haushaltszeitzone korrekte nächste Fälligkeiten
- [ ] RED: unveränderlicher `anchor_day` stellt 31. Januar → 28./29. Februar → 31. März sicher; Schaltjahr und Zeitzonenwechsel sind getestet
- [ ] RED: Enddatum, deaktivierte Serie und verpasste Fälligkeit werden respektiert
- [ ] RED: überfällige Serien erzeugen keine automatische Finanzbuchung
- [ ] RED: 30-/90-/365-Tage-Prognosen sind deterministisch
- [ ] RED: Serienupdates verlangen aktuelle Revision
- [ ] Serien-Service, Prognose und Unterdeckungswarnung implementieren
- [ ] nur bestätigte Serien in sichere Prognose aufnehmen
- [ ] GREEN: Serientests bestehen
- [ ] Commit: `feat(haushaltsbuch): Serien und Finanzprognose ergänzen`

### Task 9: Backend-API und Dashboardvertrag

- [ ] RED: alle Endpoints verlangen Auth
- [ ] RED: Create/Invite-Accept funktionieren ohne bestehende Mitgliedschaft; übrige Endpoints folgen der Autorisierungsmatrix
- [ ] RED: Nichtmitglieder sehen 404, keine fremden IDs oder Summen
- [ ] RED: Dashboard aggregiert Monat, Budgets, Serien und letzte Vorgänge
- [ ] geteilte Router registrieren und Response-Verträge stabilisieren
- [ ] OpenAPI-/Pydantic-Validierung ausführen
- [ ] GREEN: Routentests bestehen
- [ ] Commit: `feat(haushaltsbuch): V1-API vervollständigen`

### Task 10: Frontend-Shell und Haushalts-Setup

- [ ] API-/Type-Verträge an Backendmodelle anbinden
- [ ] Dummy-Inhalt durch Bereichsnavigation ersetzen
- [ ] Setup für Haushalt und Basiswährung implementieren
- [ ] Mitgliederverwaltung owner-only mit direktem Hinzufügen und Einladungscode darstellen
- [ ] Einladungscode nur unmittelbar nach Erzeugung anzeigen; Widerruf/Ablauf sichtbar machen
- [ ] owner-only JSON-Export und doppelt bestätigte irreversible Haushaltslöschung darstellen
- [ ] Loading-, Empty-, Error- und 409-Konfliktzustände abbilden
- [ ] Typecheck und Build grün
- [ ] Commit: `feat(haushaltsbuch): Haushalt und Cockpit-Navigation bauen`

### Task 11: Konten und Buchungsoberfläche

- [ ] Konten-/Kategorienansicht mit Archivierung
- [ ] Buchungsliste mit Zeitraum, Konto, Kategorie und Textfilter
- [ ] Dialoge für Einnahme, Ausgabe, Umbuchung und Split
- [ ] Storno nur nach Bestätigung
- [ ] Beträge locale-sicher parsen und als Minor Units senden
- [ ] Typecheck und Build grün
- [ ] Commit: `feat(haushaltsbuch): Buchungsoberfläche implementieren`

### Task 12: Budgets, Serien und Dashboard

- [ ] Dashboard-Kennzahlen und Prognose darstellen
- [ ] Budgetarten anlegen/bearbeiten und Perioden anzeigen
- [ ] Serien anlegen, pausieren und nächste Fälligkeiten anzeigen
- [ ] Zustände nicht ausschließlich über Farben vermitteln
- [ ] responsive Cockpit-Darstellung prüfen
- [ ] Typecheck und Build grün
- [ ] Commit: `feat(haushaltsbuch): Planung und Übersicht vervollständigen`

### Task 13: Abschlussprüfung

- [ ] vollständige Modul-Test-Suite
- [ ] Ruff, TypeScript und Produktionsbuild
- [ ] Security-Review für Auth, IDOR, Beträge, Audit und Dateipfade
- [ ] Migration auf leerer und bestehender Dummy-Installation testen
- [ ] Browser-Smoke für Setup, Buchung, Split, Storno, Budget und Mitglied
- [ ] Dateien auf Größen- und Architekturregeln prüfen
- [ ] PR erst nach grüner Verifikation mergen

## Akzeptanzkriterien

Die verbindlichen Kriterien stehen in `SPEC-V1.md`. Zusätzlich gilt:

- der separate Core-Identitätsvertrag aus Task 0 ist vor dem Modul-V1 gemergt und rückwärtskompatibel
- Dummy-Installation wird durch Modulupdate ohne Datenverlust auf V1 migriert
- V1 bleibt ohne LLM und externe Netzwerkdienste vollständig nutzbar
- der Status-Endpunkt meldet nach V1 nicht mehr `dummy`

## Nicht in diesem Plan

- Bankimport
- Belege/OCR
- Lidl Plus/PAYBACK
- automatische Wechselkurse
- Regeln/KI-Kategorisierung
- automatische Serienerkennung
