# Musicplayer R2b — Import generierter Musik aus dem Workspace

## Was
Ein Admin-Bereich „Generierte Musik" in der Buddy-Box, der alle von
`generate_music` erzeugten MP3s findet (`data_dir/workspaces/**/generated/*.mp3`)
und sie per Klick in den Player-Pool **kopiert** (Quelle bleibt unangetastet).

## Warum
Generierte Stücke liegen verstreut in Agent-/Projekt-Workspaces. Statt manuell
runter-/hochzuladen, holt der Admin sie direkt in den Player. Kopieren (nicht
verschieben), damit die Workspaces unberührt bleiben.

## Wie (grob)

### Scan-Quelle & Sicherheit
- Root: `settings.data_dir / "workspaces"` (derselbe erlaubte Media-Root wie core
  `files.py`). Nur `*/generated/*.mp3` unterhalb dieses Roots.
- Jeder Kandidat wird über `resolve()` + `relative_to(root)` geprüft → kein
  Ausbruch aus dem Workspace-Root (Symlink-/Traversal-sicher).
- Identität eines Kandidaten = sein **relativer Pfad** unter dem Root. Dieser
  Pfad wird beim Import als `source` gespeichert → schon importierte Kandidaten
  werden in der Liste als „importiert" markiert (kein Doppel-Import).

### DB
- Additiv: `ALTER TABLE module_musicplayer_tracks ADD COLUMN source TEXT DEFAULT ''`
  (Migration 002, IF-Spalte-fehlt-tolerant). `source` = relativer Quellpfad bei
  importierten Tracks, leer bei normalen Uploads.

### Backend-Routen (alle **require_admin**)
| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/generated` | Liste der gefundenen MP3s: rel_path, workspace-Label, mtime, size, already_imported |
| POST | `/generated/import` | Body `{path}` (rel. Pfad) → kopiert via storage.save_bytes, DB-Zeile mit source=path |

- Import-Titel: aus Workspace-Label + Datum, z.B. „Generiert · projects/019e… · 2026-06-24".
- Doppelter Import desselben `source` wird abgelehnt (409 already_imported).

### Frontend (Admin-only, in der Box)
- Unter dem bestehenden Upload-Button ein aufklappbarer Abschnitt „Generierte Musik"
  (Sparkles-Icon). Lädt `/generated`, zeigt Liste mit Herkunft + Datum.
- Jeder Eintrag: Import-Button (oder „✓ importiert" wenn already_imported).
  Nach Import Track-Liste **und** Generated-Liste neu laden.
- Nicht-Admins sehen davon nichts.

## Akzeptanzkriterien
- [ ] Admin sieht Liste der generierten MP3s mit Herkunft/Datum.
- [ ] Import kopiert die Datei in den Pool (Quelle bleibt), Track erscheint im Player.
- [ ] Bereits importierte Kandidaten sind als solche markiert; erneuter Import → 409.
- [ ] Pfad-Traversal/Ausbruch aus dem Workspace-Root unmöglich.
- [ ] Alles require_admin; Nicht-Admins sehen/können nichts.
- [ ] Backend-Tests grün (scan, import, dedup, traversal-guard, admin-guard).
- [ ] Alle Dateien ≤200 Z. tsc + vite grün.

## Nicht in diesem Scope
- Kein Verschieben/Löschen der Quelldateien.
- Kein Auto-Import im Hintergrund (bewusst manueller Klick).
- Kein Umbenennen importierter Titel (Kandidat später).
