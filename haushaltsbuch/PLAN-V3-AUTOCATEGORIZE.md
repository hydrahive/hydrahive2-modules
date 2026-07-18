# Plan: Auto-Kategorisierung beim Bankimport (Hybrid Historie + LLM)

## Ziel
Nach diesem Plan kann ein Import-Draft **automatisch Kategorie-Vorschläge** erzeugen —
ohne dass der User jede der mehreren hundert Zeilen einzeln kategorisiert.

Zwei Quellen, in dieser Reihenfolge:
1. **Historie** (kostenlos, deterministisch): gleicher Händler wurde schon mal gebucht →
   dieselbe Kategorie vorschlagen.
2. **LLM** (konfigurierbares Modell, lokal oder Cloud): für unbekannte Händler.
   Vor dem Call werden die Zeilen nach Händler **dedupliziert** → ein einziger Batch-Call
   für ~30–60 einzigartige Händler statt hunderte Einzel-Calls.

Vorschläge werden **nie automatisch gebucht**. Sie landen als `suggested_category_id`.
Der User übernimmt sie per 1-Klick im Review (einzeln oder alle) → dann greift der
bestehende `accepted`+`complete`-Flow unverändert.

## Kaltstart-Fall (Tills Szenario)
Neues Konto, keine Historie, mehrere hundert Buchungen:
→ Historie liefert nichts, LLM übernimmt alle einzigartigen Händler in einem Call.
→ Nach dem ersten Import ist Historie da; nachrückende/künftige Buchungen sind gratis.

## Dateien
- `migrations/003_auto_categorize.sql` — 3 Spalten auf `import_rows`: suggested_category_id,
  suggestion_source, suggestion_confidence + Index.
- `backend/categorize_history.py` — Historie-Lookup aus geposteten Transaktionen.
- `backend/categorize_llm.py` — Händler-Dedup + LLM-Batch-Call + robustes JSON-Parsing.
- `backend/categorize_service.py` — Hybrid-Orchestrierung, Persistenz der Vorschläge,
  accept-Logik.
- `backend/routes_imports.py` — 2 neue Routes: suggest, accept-suggestions.
- `backend/import_models.py` — Request-Model für accept-suggestions (+ optional model-id).
- `backend/import_persistence.py` — `_row_dict` um neue Spalten erweitern.
- `frontend/types.ts` — ImportRow um Vorschlagsfelder, neue Request-Typen.
- `frontend/api.ts` — suggestCategories, acceptSuggestions.
- `frontend/ImportBatchView.tsx` — Vorschlags-Button + Anzeige + Übernehmen.
- `tests/test_import_categorize.py` — alle neuen Backend-Pfade (LLM gemockt).

## Implementierungsreihenfolge

### Task 1: Migration + Row-Dict
- [ ] `003_auto_categorize.sql`: ALTER TABLE import_rows ADD suggested_category_id,
      suggestion_source ('history'|'llm'|NULL), suggestion_confidence (REAL).
- [ ] `_row_dict` gibt die 3 Felder mit aus.
- [ ] Test: Upload → Row hat `suggested_category_id: null`, `suggestion_source: null`.

### Task 2: Historie-Lookup
- [ ] `categorize_history.suggest(conn, household_id, rows)` → dict row_id → (cat_id, conf).
      Match-Key: counterparty_identifier (stark) sonst normalisierter counterparty (schwach).
      Nur nicht-archivierte Kategorien passenden kinds (income/expense je nach amount).
      Häufigste Kategorie des Händlers gewinnt.
- [ ] Test: Buchung mit Händler X + Kategorie K anlegen → Importzeile Händler X → Vorschlag K.

### Task 3: LLM-Batch
- [ ] `categorize_llm.suggest(household_id, rows, categories, model)` → dict row_id → (cat_id, conf).
      Dedup nach (counterparty|purpose-prefix). Prompt: Händlerliste + Kategorieliste (id,name,kind)
      → JSON [{merchant_key, category_id, confidence}]. `hydrahive.llm.client.complete` async,
      JSON-Parsing wie deepresearch/llm.parse_json. Ungültige/halluzinierte category_id verwerfen.
- [ ] Test: `complete` gemockt (monkeypatch) → deterministische Zuordnung geprüft.

### Task 4: Hybrid-Service + Persistenz
- [ ] `categorize_service.suggest_categories(batch_id, model, principal)`:
      lädt draft-rows ohne category_id/ohne Vorschlag; erst Historie, Rest via LLM;
      schreibt suggested_category_id/source/confidence; audit. Nur status='draft'.
- [ ] Test: gemischter Fall — ein Händler aus Historie, einer per LLM.

### Task 5: Accept-Suggestions
- [ ] `categorize_service.accept_suggestions(batch_id, revision, row_ids|None, principal)`:
      setzt category_id = suggested_category_id und status='accepted' für gewählte/alle
      Zeilen mit Vorschlag (nur wenn kind passt & keine Fehler). Optimistic revision.
- [ ] Test: accept all → Zeilen accepted mit korrekter category_id; complete danach grün.

### Task 6: Routes + Models
- [ ] `POST /imports/{id}/suggest-categories` (Body: optional model) → aktualisierter Batch.
- [ ] `POST /imports/{id}/accept-suggestions` (Body: revision, optional row_ids) → Batch.
- [ ] Models: `ImportSuggest`, `ImportAcceptSuggestions`.
- [ ] Test: 404 für Fremd-Haushalt, 409 bei non-draft.

### Task 7: Frontend
- [ ] types: ImportRow += suggested_category_id/source/confidence; Request-Typen.
- [ ] api: suggestCategories, acceptSuggestions.
- [ ] ImportBatchView: Button „Kategorien vorschlagen" (Draft), Badge/Anzeige des
      Vorschlags je Zeile, „Alle Vorschläge übernehmen".
- [ ] Typecheck + Build grün.

## Akzeptanzkriterien
- [ ] Kaltstart: mehrere hundert Zeilen → 1 LLM-Call → alle einzigartigen Händler zugeordnet.
- [ ] Zweiter Import desselben Händlers → Historie-Vorschlag ohne LLM.
- [ ] Kein Vorschlag wird automatisch gebucht; complete-Flow unverändert.
- [ ] LLM-Fehler/kein Modell → sauberer Fehler, Historie-Vorschläge bleiben erhalten.
- [ ] Alle bestehenden Tests grün; neue Tests grün; hh-review ok; Build grün.

## Nicht in diesem Plan
- Auto-Buchen ohne Bestätigung (bewusst ausgeschlossen).
- Regel-Editor / manuelle Händler→Kategorie-Mappings (späteres V4).
- Lidl-Plus / PAYBACK-Anreicherung.
- Konfidenz-Schwellen-UI (fix im Code, kein Setting im MVP).
