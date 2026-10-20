# Bauplan L1 – Gesetzeskorpus, Suche, Werkzeuge, Gesetzes-Ansicht

Spec: `legal/SPEC-LEGAL.md` §4.1, §6, §6a (L0-Messung) · Task f0b8d254 · Version 0.1.0

**Ziel L1:** Bundesgesetze liegen lokal mit Stand vor. Mensch und Agent finden Normen per Suche und bekommen
den Wortlaut belegt. Fälle, Fristen und Briefe gehören nicht zu L1, sondern zu L2/L3.

## Dateien

```
legal/
  manifest.json                 id legal, 0.1.0, vault true, capabilities, default_agent_tools false
  migrations/001_corpus.sql     module_legal_laws, module_legal_norms, module_legal_norms_fts (FTS5)
  backend/
    __init__.py                 register: router, tools, job, migrations
    corpus_list.py              Kernliste (54 Kürzel aus der Spec), Rubriken
    gii_parse.py                XML → Normen (amtabk, enbez, titel, gliederung, text); nur stdlib
    gii_fetch.py                toc + xml.zip laden (safe_async_client, User-Agent, Pause, Größenlimit)
    corpus_store.py             Gesetz speichern: Hash-Vergleich, alte Fassung mit valid_to behalten
    corpus_sync.py              Job: Kernliste + nachgeladene Gesetze aktualisieren, Fortschritt
    search.py                   FTS5-Suche + exakte Norm-Erkennung („536c BGB“, „§ 536 c BGB“, „BGB 536c“)
    routes.py                   /laws, /laws/{abk}, /norms/{abk}/{enbez}, /search, /sync (Admin)
    tools.py                    legal_search, legal_norm
  frontend/
    index.tsx                   nav „Recht“, routes /recht/*
    LegalPage.tsx               Reiter Gesetze (L1); Fälle folgen in L2
    LawSearch.tsx, NormView.tsx, api.ts
  tests/                        conftest + _hh_isolation (Kopie), Fixtures mit echtem XML-Ausschnitt
```

## Schritte (TDD: erst rote Tests als eigener Commit)

1. **Parser** (`gii_parse`). Tests mit XML-Ausschnitten aus BGB, VwGO, OWiG und BetrKV, gespeichert unter
   tests/fixtures:
   - `amtabk` vor `jurabk` („OWiG“ statt „OWiG 1968“)
   - Gliederung wird an die folgenden Normen vererbt
   - Inhaltsübersicht, „(weggefallen)“ und leerer Text werden übersprungen
   - Listen `DL/DT/DD` mit Zeilenumbruch, Absätze `(1)`, `(2)` bleiben getrennt
   - Fußnoten bleiben aus dem Text
   - Stand aus `standangabe/standkommentar`
2. **Normbezeichnung** (`search.parse_citation`), Tests:
   - `§ 536c BGB`, `§536c BGB`, `536c BGB`, `BGB § 536c`, `§ 536 c BGB`, `Art. 3 GG`
   - `§ 70 VwGO`, `§ 67 OWiG`, `§ 1 KSchG`
   - Groß-/Kleinschreibung des Kürzels egal
   - unbekanntes Kürzel ergibt `None`
3. **Store** (`corpus_store`). Tests:
   - Erstimport
   - gleicher Hash ändert nichts
   - neuer Stand: alte Normen bekommen `valid_to`, neue `valid_from`
   - die Suche findet nur gültige Normen, `legal_norm` mit `as_of` die alte Fassung
3b. **Suche**, Tests auf einer Mini-Fixture mit ca. 30 Normen: Fachbegriffe treffen, Präfix-Suche
   („Mietsicherh“), Gliederung als Suchfeld, Kürzel-Filter, Limit, leere Anfrage ist ein Fehler.
   Zitat-Eingabe („536c BGB“) liefert sofort die exakte Norm.
4. **Fetch**. Tests mit gefälschtem Client:
   - nur `https://www.gesetze-im-internet.de/<kürzel>/xml.zip`, Kürzel aus der toc
   - bei fremdem Host keine Verbindung
   - ZIP größer als 20 MB wird abgelehnt
   - ZIP mit mehreren XML oder ohne XML ist ein Fehler
   - Zip-Slip ist ausgeschlossen, weil nur im Speicher gelesen wird
5. **Sync-Job**:
   - läuft täglich 03:30 (Prüfung jede Stunde, Lauf nur wenn letzter Lauf älter als 20 h)
   - erster Lauf beim Start nach 120 s, falls der Korpus leer ist
   - Fortschritt in `module_legal_sync`
   - Fehler bei einem Gesetz bricht nicht alles ab
   - Admin-Route `POST /sync` startet sofort
6. **Routen + Rechte**. Tests:
   - ohne `module.legal` gibt es 403 (Kern-Tor)
   - mit Login, aber ohne Vault-Token gibt es 423 (Kern, Manifest `vault`)
   - Lesen geht für jeden mit `module.legal`
   - `/sync` nur für Admins
7. **Werkzeuge**:
   - `legal_search` mit query, law?, limit≤20. Beschreibung: in Fachbegriffen suchen,
     Wortverbindungen getrennt (L0 §6a)
   - `legal_norm` mit citation oder law+enbez, optional as_of. Liefert Wortlaut, Stand, Abrufdatum und
     amtlichen Link
   - Tests: Treffer, unbekannte Norm, Kürzel-Filter, Längenbegrenzung
   - Stufe `normal`, weil Gesetze öffentlich sind
8. **Frontend**, Reiter „Gesetze“:
   - Suche mit Ergebnisliste (Kürzel, §, Überschrift oder sonst Gliederung)
   - Norm-Ansicht mit Absätzen, Stand und Link zu gesetze-im-internet
   - Kopierknopf für „§ 536c BGB“
   - Hinweis „Keine Rechtsberatung“
   - vitest für parseCitation-Anzeige und Ergebnisliste

## Prüfung vor dem PR

- pytest Modul-Suite (Kern-venv), ruff, `check_test_safety`, `check_version_bump` (neues Modul).
- Mutanten:
  - amtabk/jurabk-Reihenfolge
  - Weggefallen-Filter
  - Hash-Vergleich
  - valid_to-Fortschreibung
  - Host-Prüfung im Fetch
  - Größenlimit
  - Admin-Prüfung bei /sync
  - Fachbegriff-Gewichtung bm25
- **Echter Lauf auf hydratest:**
  - Modul installieren, Sync über die Kernliste mit Dauer und Normzahl
  - die 20 L0-Fragen (Fachbegriffe) über `legal_search`: mindestens 19/20 in den Top 5
  - § 536c BGB im Browser mit Wortlaut gleich der amtlichen Seite
