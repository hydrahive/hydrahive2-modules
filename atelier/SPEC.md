# Atelier — Media-Generierung mit Charakter-Konsistenz

## Problem

Till will mehrteilige Bild-/Video-Serien generieren, in denen **dieselben
Figuren und das CI** konsistent bleiben. Aktuell erzeugt jeder Generierungs-Aufruf
unabhängige Bilder ohne gemeinsamen Anker — Figuren driften, Stil wechselt.
Es fehlt (1) ein Ort, der Charaktere + CI als wiederverwendbare Anker bündelt,
und (2) ein Generator, der die starken Konsistenz-Hebel (Referenzbild, Seed,
fester Steckbrief/Style) sauber nutzt.

## Lösung (Kurz)

Eigenes Modul **`atelier`** — eine Media-Generierungs-Seite (eigener Nav-Punkt
oben, nicht im Settings-Hub), mit:
- **Projekt-Auswahl** (wie im Buddy/Chat): alles was im Atelier entsteht, landet
  im Medien-Verzeichnis des gewählten Projekts.
- **Charakter-/CI-Bibliothek** pro Projekt: Figuren mit Steckbrief, Hero-
  Referenzbild(ern), Style-Anchor, Farbpalette, Seed.
- **Generator** über OpenRouters dedizierte Image-API (`/api/v1/images`) mit
  `seed` + `input_references` (mehrere Referenzbilder) — der eigene, stärkere
  Generator des Moduls (Variante b: Core-`generate_image` bleibt unangetastet).

## Warum eigener Generator (nicht Core-Tool umbauen)

Till's Wahl (b): Das Atelier ist ein eigenständiges Werkzeug mit eigenem
`/api/v1/images`-Client. Der Buddy-Chat behält sein simples `generate_image`
(chat-Pfad). Kein Risiko fürs Core, klare Trennung. Den OpenRouter-Key liest
das Modul aus der zentralen Config (settings, wie das Core-Tool).

## Projekt-Bindung (Tills Wunsch)

- Oben auf der Seite ein **Projekt-Dropdown** (`projectsApi.list()`).
- Speicherort: `<projekt-workspace>/atelier/` mit Unterordnern:
  - `characters/<char-id>/` — Referenzbilder + character.json
  - `output/` — generierte Bilder/Videos (Galerie)
  - `ci.json` — CI-Kit des Projekts (Palette, Style-Anchor, Default-Modell)
- `ensure_workspace(project_id)` existiert bereits → Pfad
  `data_dir/workspaces/projects/<id>/atelier/`.
- Ohne gewähltes Projekt: Hinweis "Projekt wählen" (kein globaler Müll-Ordner).

## Datenmodell

Dateibasiert im Projekt-Workspace (kein DB-Zwang, bleibt beim Projekt, einfach
zu sichern/exportieren):

```
character.json:
  { id, name, description (Steckbrief, verbatim),
    style_anchor, palette: ["#..", ..], seed?, model?,
    references: ["characters/<id>/hero1.png", ..] }

ci.json:
  { palette: [...], style_anchor, default_model, aspect_ratio }
```

Galerie-Metadaten je Output als Sidecar `output/<name>.json`:
`{ prompt, character_ids, seed, model, references, created_at }` —
damit jedes Bild reproduzierbar/nachvollziehbar ist.

## Architektur

```
atelier/
  manifest.json            # icon "Palette", nav_group "working"
  backend/
    __init__.py            # register: router + (keine Migration nötig, dateibasiert)
    routes.py              # /api/modules/atelier/* (require_auth, project-scoped)
    storage.py             # Pfade im Projekt-Workspace, ownership über Projekt-Mitgliedschaft
    characters.py          # CRUD character.json
    generate.py            # OpenRouter /api/v1/images-Client (seed, input_references)
    models_cache.py        # /api/v1/images/models — welches Modell kann seed/refs
  frontend/
    index.tsx              # routes + nav (oben) + i18n
    AtelierPage.tsx        # Projekt-Picker + Layout
    CharacterLibrary.tsx   # Figuren anlegen/wählen (links)
    GeneratePanel.tsx      # Prompt + Figuren-Auswahl + Parameter (mitte)
    Gallery.tsx            # generierte Medien des Projekts (rechts/unten)
    api.ts, types.ts
```

## Generierungs-Flow (Konsistenz)

1. Projekt wählen → CI-Kit + Charaktere laden.
2. Figur(en) für die Szene auswählen (Multi).
3. Szene beschreiben (nur das Variable: "am Strand", "kämpfend").
4. Modul baut den **vollen Prompt**: `style_anchor` (CI) + Figur-Steckbrief(e)
   (verbatim) + Szene; hängt die **Hero-Referenzbilder** als `input_references`
   an; setzt `seed` (falls Modell es kann) + Palette-Hinweis.
5. Generiert über `/api/v1/images`, speichert nach `output/` + Sidecar.
6. Galerie zeigt das Ergebnis; "als neue Referenz übernehmen" möglich
   (Hero-Shot-Workflow: erstes gutes Bild wird Anker der Serie).

## Konsistenz-Hebel (umgesetzt)

| Hebel | Umsetzung |
|-------|-----------|
| Referenzbild (stärkster) | `input_references` (mehrere Hero-Shots je Figur) |
| Verbatim-Steckbrief | character.description unverändert in jeden Prompt |
| Style-Anchor / CI | ci.style_anchor + palette in jeden Prompt |
| Seed | pro Figur gespeichert, an API durchgereicht (modellabhängig) |
| Gleiches Modell | ci.default_model / character.model |

## Video (Phase 2b, später)

Image-to-Video mit dem generierten/gewählten Bild als Startframe (Core hat
`generate_video` mit `image_path` — image-to-video bei Kling/Hailuo). Erst
Bilder solide, dann Video als Ausbaustufe.

## Nicht im Scope (v1)

- Kein eigenes Modell-Training/LoRA (nur Prompt+Referenz-basierte Konsistenz).
- Kein universeller Negativ-Prompt (OpenRouter-API kennt ihn nicht standardisiert;
  modellabhängig über provider.options — später optional).
- Buddy-`generate_image` bleibt unangetastet.

## Akzeptanzkriterien

1. Projekt-Dropdown oben; ohne Auswahl klarer Hinweis.
2. Charakter anlegen (Steckbrief, Style, Palette, Hero-Referenz hochladen/generieren).
3. Szene generieren mit gewählter Figur → Bild landet in
   `<projekt>/atelier/output/` + Sidecar mit allen Parametern.
4. Referenzbild wird real als `input_references` mitgeschickt (image-to-image).
5. Galerie zeigt projektgebundene Medien; Bild als neue Referenz übernehmbar.
6. Eigener `/api/v1/images`-Client; Core-Tool unberührt.
7. tsc + vite build grün; Backend-Tests grün; Dateien < 200 Zeilen.
```
