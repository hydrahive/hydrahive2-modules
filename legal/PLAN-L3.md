# Bauplan L3 – Brief-Werkstatt, Schriftverkehr, Prüfliste, Druckansicht

Spec: `SPEC-LEGAL.md` §4.2 (Schriftverkehr), §4.5 (Zitat-Prüfer, Teil), §4.6 (`legal_propose_letter`, Skill),
§4.7 (Brief-Werkstatt). Pilot: Mangelanzeige Mietsache (Task 5d49bee3). Stand der Befunde: 20.10.2026.

## Befunde vor dem Bau

- **L2 ist live** (.2: 0.2.0, Fall ohne Modellangabe + echter Agent-Lauf geprüft 20.10.; 0.2.1 Modellwahl = PR #243).
  Vorschläge gibt es für `party|deadline|fact` (`proposals.py`). Ein Brief wird eine vierte Vorschlagsart `letter`,
  gleiche Mechanik: Agent legt ab, Mensch übernimmt.
- **Abweichung von der Spec, bewusst:** Spec §4.6 nennt `fetch_url` für den Rechts-Agenten. L2 hat ihn weggelassen
  (`OUTWARD_TOOLS`, Vault-PIN). Bleibt so.
- **Skills aus Modulen:** Der Kern lädt keine Modul-Skills. `mining` und `diagramme` synchronisieren selbst
  (`backend/skill_sync.py` → `hydrahive.skills._defaults_sync.sync_defaults` nach `system_dir()`, mit
  `skills/_history.json` aus `scripts/update_skill_history.py`). Skill `rechtsbrief` geht denselben Weg.
- **Migrationen** laufen je Datei mit `executescript` (`modules/migrations.py`); SQLite kann einen CHECK nicht per
  ALTER ändern → für `kind='letter'` Tabelle neu anlegen + kopieren, in derselben Datei.
- **PDF:** keine Bibliothek im Kern-venv; Till 20.10.: Druckansicht im Browser reicht (CSS `@page`, DIN 5008 Form B).
- **Gegenlesen** (zweiter LLM-Durchgang) ist laut Spec-Tabelle **L4**, nicht L3. Bleibt dort.
- **Zitat-Prüfer:** `citation.parse_citation` erkennt eine Norm je Aufruf. L3 braucht das Finden *aller* Normen in
  einem Brieftext (inkl. `§§ 535 ff.`, `Abs./S./Nr.`). Wörtliche Zitate gegen den Normtext prüfen = L4.

## Datenmodell (`migrations/003_letters.sql`)

```
module_legal_correspondence  id, project_id, direction(in|out), status(draft|sent|received), date, sender, recipient,
                             subject, body, delivery(''|einwurf_einschreiben|einschreiben_rueckschein|bote|fax|mail|
                             brief|persoenlich), proof, letter_type, check(JSON), created_by, created_at, updated_at
module_legal_proposals.kind  + 'letter'  (CHECK neu anlegen: SQLite kann CHECK nicht ändern → Tabelle umbauen,
                             Daten kopieren, in einer Transaktion; Test mit vorhandenen Vorschlägen)
```

- Eingehende Schreiben trägt der Mensch ein (Datum, Absender, Betreff, Text abschreiben/kurz). Kein Upload (L5).
- Ausgehend: aus übernommenem Brief-Vorschlag (Status `draft`) oder direkt geschrieben. „Versendet am … per …“ setzt
  `sent` + `date` + `delivery` + `proof`. **Kein automatischer Versand.**
- Orphan-Job (`orphans.py`) sichert/löscht die neue Tabelle mit.

## Schritte (TDD, rote Tests als eigener Commit)

1. **Normen in Text finden** (`citation.find_all(text)`): alle Normbezeichnungen mit Position; je Fund belegt/unbekannt
   gegen den Korpus. Tests: 20 Formen (`§ 536c BGB`, `§§ 535 ff. BGB`, `§ 536 Abs. 1 S. 2 BGB`, `Art. 3 GG`,
   `§ 7 SGB II`, ohne Gesetz → kein Fund, Fließtext mit „§“ ohne Nummer → kein Fund), Positionen stimmen.
2. **Prüfliste** (`letter_check.py`, ohne KI) → Liste `{key, ok, hint}`:
   - Absender (Name + Anschrift), Empfänger (Name + Anschrift), Datum
   - Betreff; Aktenzeichen, falls der Fall eins hat
   - **Frist als Datum**: „binnen/innerhalb … Tagen/Wochen“ ohne Datum (TT.MM.JJJJ) → Hinweis; Datum in der
     Vergangenheit → Hinweis
   - Normen belegt (Schritt 1), unbekannte rot, **blockieren nicht**
   - Zustellweg vermerkt; Anlagenliste, wenn „Anlage“ im Text
   Tests je Punkt positiv/negativ.
3. **Vorlagen** (`letter_templates.py`): Mangelanzeige mit Fristsetzung (Pilot), Fristsetzung/Mahnung, Widerspruch
   gegen Bescheid, Kündigung, Bitte um Akteneinsicht, Anschreiben an eigenen Anwalt. DSGVO-Auskunft erst mit
   EUR-Lex-Quelle (Spec §8) → nicht in L3. Vorlage = Gerüst mit Platzhaltern aus der Fallakte (Absender = Rolle `me`,
   Empfänger = gewählter Beteiligter, Aktenzeichen, Bundesland/Ort, heutiges Datum, Frist aus der Akte). Normtexte in
   der Vorlage nur als Verweis, mit Korpus-Beleg im Test.
4. **Schriftverkehr + Brief-Vorschlag** (`correspondence.py`, `proposals.py`): CRUD, Statuswechsel,
   `propose(kind='letter')` speichert Text + Prüfliste; Übernehmen → Schriftverkehr `out/draft`.
   Tests: Rollen wie L2, fremde IDs 404, Übernehmen legt genau einen Eintrag an, Migration erhält alte Vorschläge.
5. **Werkzeuge**: `legal_propose_letter` (Brieftyp, Empfänger-ID, Betreff, Text), `legal_check_letter` (Prüfliste für
   einen Entwurf, speichert nichts). `legal_case` liefert den Schriftverkehr mit. Beide `privat`.
   Tests: ohne Projekt/fremdes Projekt/`read` wie L2; Vorschlag ändert Schriftverkehr nicht.
6. **Skill `rechtsbrief`** (`skills/rechtsbrief.md` + `skill_sync.py` + `_history.json`): Aufbau je Brieftyp, Ton
   (sachlich, ohne Drohungen), Pflichtangaben, „erst Normen mit legal_norm holen, Frist als Datum mit legal_deadline,
   Zustellweg Einwurf-Einschreiben empfehlen“. Agent-Anweisung (`agent_profile.py`) verweist auf den Skill.
7. **Routen**: `/cases/{pid}/correspondence` (CRUD, `PATCH …/sent`), `/cases/{pid}/letters/check` (Prüfliste für
   Text), `/letters/templates` + `/cases/{pid}/letters/draft?template=…` (Gerüst aus der Akte).
8. **Oberfläche**:
   - Reiter **Schriftverkehr** in der Fallakte: Liste ein/aus mit Datum, Status, Zustellweg; „Eingang erfassen“;
     „Neuer Brief“ (Vorlage wählen → Editor mit Gerüst).
   - **Brief-Editor**: Text links, Prüfliste rechts (live), unbekannte Normen rot; „Als Entwurf speichern“,
     „Druckansicht“, „Versendet am … per …“.
   - **Druckansicht**: eigene Seite, DIN 5008 **Form B**, `window.print()`. Maße (falzmarke.com/din-5008, abgerufen
     20.10.2026, dort „mehrfach bestätigt“ über Wikimedia-Maßzeichnung Form B + Onlineprinters-Magazin; Abgleich mit dem
     kostenpflichtigen Normtext steht laut Quelle aus): A4 210×297 mm; Briefkopf 45 mm; Anschriftfeld 85×45 mm, linke
     Kante 20 mm, Text ab 25 mm, darin Rücksendeangabe 5 mm, Zusatz-/Vermerkzone 12,7 mm, Anschriftzone 27,3 mm;
     Informationsblock x = 125 mm, Breite 75 mm, Oberkante 50 mm; Ränder links 25 mm, rechts 20 mm (Textbreite 165 mm);
     Falzmarken 105 und 210 mm, Lochmarke 148,5 mm; Grundzeile 4,23 mm (12 pt); Betreff zwei Leerzeilen unter dem
     tieferen von Feld und Block. Seitenzahl auf Folgeseiten. Abnahme: PDF ausmessen.
   - Vorschläge-Reiter zeigt Brief-Vorschläge mit Prüfliste.
   - vitest: Prüflisten-Anzeige, Druck-Layout-Hilfen (Datum, Bezugszeichen), Formular.

## Prüfung vor dem PR

- pytest, ruff, `check_test_safety`, `check_version_bump` (0.3.0), vitest/tsc/eslint im Kern-Worktree.
- **Mutanten:** Frist ohne Datum gilt als ok · unbekannte Norm gilt als belegt · `read` darf Brief übernehmen ·
  Übernehmen legt zwei Einträge an · Migration verliert Vorschläge · Orphan-Job vergisst Schriftverkehr.
- **Pilot (Abnahme laut Spec):** auf hydratest Fall „Mietsache Hitze“, Agent schreibt Mangelanzeige mit Fristsetzung
  (Skill geladen, § 536c belegt, Frist als Datum, Einwurf-Einschreiben), Mensch übernimmt, Druckansicht als PDF
  gespeichert und angesehen (Anschriftfeld sitzt im Fenster eines DIN-lang-Umschlags: Maße prüfen).
- Danach Till: echter Fall (Task 5d49bee3) – fehlende Daten (Namen/Anschriften, Datum Sprechstunde, Baujahr, seit wann)
  liefert er.

## Entscheidungen (Till, 20.10.2026)

1. **Eingang erfassen:** Abschreiben bzw. Kurzfassung reicht bis L5 (Upload/OCR).
2. **Vorlagen:** Die 6 Vorlagen reichen (ohne DSGVO, bis EUR-Lex geklärt ist).
3. **Absender:** je Fall, als Beteiligter mit Rolle „Ich / wir“ (`me`).
