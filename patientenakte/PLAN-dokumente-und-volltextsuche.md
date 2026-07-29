# Plan: Dokumente-Upload + OCR/PDF-Textextraktion + FTS5-Volltextsuche

**Stand:** 2026-07-29 · **Modul:** `hydrahive2-modules/patientenakte` (v1.0.2)

> Ersetzt die veralteten GitHub-Issues #167–#173 und #166. Jene verweisen noch
> auf `core/src/hydrahive/patientenakte/`, den Branch `feat/akte-dokumente` und
> `docs/superpowers/plans/2026-05-30-patientenakte-phase3.md`. **Alle drei
> existieren nicht mehr** — die Akte ist ins eigenständige Modul ausgelagert.
> Dieser Plan bildet den echten aktuellen Modul-Stand ab.

## Ist-Zustand (verifiziert)

Vorhanden im Modul-Backend:
- `entities.py` — generisches registry-getriebenes CRUD (`create`/`update`/`delete`,
  Zeilen 103/147/155), BEGIN-IMMEDIATE-Transaktionen, keine SQL-Injection-Fläche
- `patients.py`, `schema.py` (ENTITIES-Registry), `routes.py`, FHIR-/eGA-/Health-Stack
- Migrationen: `001_patientenakte.sql`, `002_fhir_ega.sql`, `003_health.sql`
- Generische Entity-Routen in `routes.py`: `GET/POST /{entity}` (Z.105/116),
  `GET/DELETE /{entity}/{eid}` (Z.136/159)

**Fehlt komplett:** Dokument-Upload, Datei-Storage, PDF-/OCR-Textextraktion,
FTS5-Volltextsuche, Audit-Log, Export/DSGVO.

## Abhängigkeitskette

```
A (Dokumente 3a) ─▶ B (Volltextsuche 3b) ─▶ C (DSGVO Phase 4, optional/später)
```

FTS (B) macht ohne extrahierten Dokument-Text (A) nur die halbe Miete —
deshalb A zuerst.

---

## Block A — Dokumente (ehemals #167–#169)

### A1 · Datei-Storage `backend/documents.py` (NEU)
- Storage-Verzeichnis pro Patient unter `HH_DATA_DIR` (siehe wie andere Module
  ihr Datenverzeichnis auflösen — **nicht** hart `/var/lib/...`).
- `create_with_file(user_id, pid, file_bytes, filename, meta)`:
  - Extension-Guard (Allowlist: pdf, png, jpg, jpeg, txt), Größen-Guard
  - Datei mit Rechten `0o600` speichern, Dateinamen nie aus User-Input als Pfad
  - Entity-Zeile über `entities.create(...)` anlegen (neue Entity `dokument` in
    `schema.py` ENTITIES-Registry mit Feldern: titel, typ, datum, mime,
    filename, size, ocr_text)
- `open_file(user_id, pid, eid)` → (bytes, mime, filename); `FileNotFoundError`/
  `PermissionError` sauber propagieren (Route macht daraus 404)
- `delete(user_id, pid, eid)` → Entity + Datei löschen

### A2 · PDF/OCR-Textextraktion
- Dependency `pypdf` (in Modul-`pyproject.toml`/Requirements des Moduls
  eintragen — prüfen wie das Modul Abhängigkeiten deklariert).
- Bei Upload eines PDF: Text extrahieren → `ocr_text`-Feld füllen (Grundlage
  für FTS). Für Bilder optional später echtes OCR (tesseract) — v1: nur PDF-Text.

### A3 · Routen in `routes.py` — **VOR** der generischen `/{entity}`-Route
- `POST /documents/upload` (multipart: `file` + Form `titel/typ/datum`)
- `GET /documents/{eid}/file` → `FileResponse` (mime + filename), 404-Handling
- `DELETE /documents/{eid}`
- ⚠️ Reihenfolge kritisch: generische `@router.get("/{entity}")` (Z.105) fängt
  sonst `/documents/...` ab. Spezifische Routen müssen davor registriert werden.

### A4 · Frontend
- `frontend/api.ts` — `uploadDocument(file, meta)` (FormData),
  `downloadDocument(eid)` (fetch→Blob, Bearer aus Auth-Store), `deleteDocument(eid)`
- `frontend/views/AkteDocuments.tsx` (NEU) — Upload-Button (Muster:
  `components/ImportButton.tsx`), Liste, "Ansehen" (Blob→ObjectURL→neuer Tab),
  "Löschen"
- `AkteSidebar.tsx` — Eintrag "Dokumente"; `AktePage.tsx` — Route

### A5 · Verifikation + Deploy
- **Isolierter E2E** (eigenes `HH_DATA_DIR=/tmp/...`, NIE Prod-Pfad/Port):
  Akte anlegen → PDF hochladen → `ocr_text` gefüllt? → Download = Originalbytes?
  → Löschen entfernt Datei
- `manifest.json` Version hochzählen (sonst kein Update erkannt!)
- pytest grün, ruff grün

---

## Block B — Volltextsuche (ehemals #170–#173)

### B1 · FTS5-Migration + `search.py`
- `migrations/004_akte_fts.sql`:
  ```sql
  CREATE VIRTUAL TABLE akte_fts USING fts5(
    patient_id UNINDEXED, entity UNINDEXED, entity_id UNINDEXED,
    label, content, tokenize='unicode61 remove_diacritics 2');
  ```
- `backend/search.py` — service-seitig (keine SQL-Trigger), importiert nur
  `schema` + `db` (zyklenfrei):
  - `_content(spec, record)` — alle Textfelder eines Records zusammenführen
  - `index_entity` / `unindex_entity` / `search(user_id, pid, q)`
  - `backfill_if_empty()` (idempotent)
- FTS5 ist verfügbar (SQLite 3.45.1, ENABLE_FTS5).

### B2 · Index-Hooks in `entities.py`
- `create`/`update` am Ende `search.index_entity(...)`, `delete`
  `search.unindex_entity(...)`.
- Import so legen, dass **kein Zyklus** entities↔search entsteht: `search`
  importiert NICHT `entities` → top-level import in `entities` ist ok.
- `documents.create_with_file`/`delete` erben das automatisch.

### B3 · Such-Route
- `GET /search?q=` — **VOR** generischer `/{entity}`-Route.
- `pid = patients.get_own_id(auth[0])`; leeres `q`/keine Akte → `[]`.

### B4 · Frontend Such-View + Backfill
- `api.ts` `search(q)`; `views/AkteSearch.tsx` (debounced ~250ms, nach Entität
  gruppiert, Klick→Listen-Route); Sidebar-Eintrag "🔎 Suche".
- Backfill beim Init (idempotent).

---

## Block C — DSGVO Phase 4 (ehemals #166, optional/später)
- Audit-Log-Migration + `audit.py` (log in jede Lese-/Schreiboperation)
- Verschlüsselung-at-rest via `credentials/_crypto.py`
- Vollexport JSON + PDF; `DELETE /patients/{pid}` (Recht auf Löschung)
- Security-Audit: PHI, Auth, Injection, Audit-Vollständigkeit

---

## Arbeitsweise (verbindlich)
- Pro Block ein Branch + ein PR, CI grün (tsc, eslint, pytest, ruff, spec-guard)
- Vor Code: `manifest.json`-Version bump nicht vergessen
- E2E immer isoliert, nie gegen Prod (Port 8001 / `/var/lib/hydrahive2`)
- Deploy führt till aus (Agent hat kein passwordless sudo)
