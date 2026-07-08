# Plan: Atelier-Buddy-Tools + Skill (Media-Werkstatt per Chat steuern)

> Status: DESIGN / PLANUNG. Noch kein Code. Ziel: der Buddy (Chat-Agent) kann
> alles anlegen/vorbereiten, was das Atelier-Backend kann — und der User lässt
> die eigentliche Generierung dann im Atelier (oder direkt per Tool) laufen.

## Problem
Der Buddy kennt das Atelier heute nicht. Man muss jede Figur, jeden Prompt, jede
Szene von Hand in der UI klicken. Gewünscht: mit dem Buddy reden — er legt
Charaktere an, geht Prompts durch, kennt die verfügbaren Modelle (A–Z-Liste je
Kategorie), liest die vorhandenen Atelier-Inhalte (Galerie, Charaktere, Szenen)
und bereitet alles vor. Der Mensch behält die Kontrolle (Freigabe/Feinschliff im
Atelier), der Buddy macht die Fleißarbeit.

## Bestehende Bausteine (kein Neubau nötig)
- **Atelier-Backend** deckt fast alles ab (43 Endpoints): Charaktere CRUD, CI,
  generate (Bild), gallery, videos, films, audio/generate, audio/profiles,
  screenplay/scenes/shots/decompose/render, promote, continue.
- **Modul-Tool-API**: `ctx.register_tool(Tool(...))` in `register(ctx)` — Buddy
  sieht Modul-Tools automatisch, wenn Atelier aktiv ist. `ToolContext` liefert
  `user_id`, `project_id`, `workspace`.
- **Modell-Listen live**: `media_models.list_{image,video,audio}_models()` +
  `list_speech_models()` → A–Z-Liste je Kategorie (wie das Backend-Dropdown).
- **Tool-Muster**: `core/src/hydrahive/tools/generate_speech.py` (Schema +
  async _execute + `Tool(...)`, category="media").

## Designprinzip
**Die Tools rufen die Atelier-Backend-Funktionen direkt auf** (nicht über HTTP,
sondern die Python-Ebene: `characters.create_character`, `service.generate_for_project`,
`music.generate_for_project`, `screenplay.*`, `director.*`). Kein zweiter
Code-Pfad, keine Logik-Duplikation. Auth/Guard: Tools laufen im Kontext des
Users → `project_id` kommt aus `ToolContext`; Zugriffscheck via
`storage.user_can_access(user_id, project_id)`.

## Scope-Entscheidung (Till, 2026-07-08): NUR A + B — KEINE Generierung
Der Buddy **voreinstellen/anlegen**, aber **NICHTS auslösen**: keine Bilder,
keine Videos, keine Musik, keine Film-Renders. Das Auslösen bleibt beim User im
Atelier. → **Ebene C ist aus v1 gestrichen.**

- **Ebene A — Lesen (risikolos):** Projekte, Modelle (A–Z je Kategorie),
  Charaktere, Galerie, Szenen, Overview.
- **Ebene B — Voreinstellen/Anlegen (persistiert, günstig):** Charaktere, CI/Stil,
  Screenplay-Kopf, Szenen. Schreibt nur Config-Dateien, startet keine Jobs.

### Persistiert vs. transient (Tills Overlay-Einwand)
Der Buddy kann nur **persistierte** Einstellungen setzen. Was live im Generier-
Overlay eingegeben wird, kann er NICHT speichern — ABER die Overlays erben ihre
Defaults aus CI + Charakter. Stellt der Buddy CI/Charaktere sauber ein, sind die
Overlay-Vorauswahlen (Modell, Aspect, Seed) beim Öffnen schon richtig belegt.

- **Persistiert (Buddy setzt):** Charakter (name, description, style_anchor,
  palette, seed, model, Referenzen-Upload NICHT), CI (default_model, aspect_ratio,
  style_anchor, palette), Screenplay-Kopf (title, film_model, audio_model,
  voice_model, aspect, default_duration), Szene (description, character_ids,
  dialogues, music-Flag+prompt, camera, location, time_of_day).
- **Transient (Buddy setzt NICHT, liefert höchstens kopierbaren Text):**
  Bewegungs-Prompt im Video-Overlay, konkrete Szene-Eingabe beim Bild-Generieren,
  Start-/Endbild-Auswahl, Dauer pro Einzel-Clip.

## Tool-Liste (Vorschlag — Namen final beim Bau)

### A. Kontext & Listen (Lese-Tools)
1. `atelier_projects` — welche Projekte hat der User (id + name), welches ist aktiv.
2. `atelier_models` — Modelle je Kategorie {image|video|audio|speech} als A–Z-Liste
   (id, name, + bei video: durations/aspect_ratios/frame_images). = das Backend-Dropdown.
3. `atelier_overview` — Snapshot eines Projekts: CI (style_anchor, palette,
   default_model), #Charaktere, #Galerie-Bilder, #Videos, #Szenen, Screenplay-Kopf.
4. `atelier_characters` — Charaktere eines Projekts (Steckbriefe, Style-Anchor,
   Seed, Modell, #Referenzen).
5. `atelier_gallery` — Galerie-Bilder (rel, prompt, seed, model) — Buddy kann
   "lies mein Atelier" erfüllen, Prompts wiederverwenden.
6. `atelier_scenes` — Drehbuch-Kopf + Szenen + (optional) Shots.

### B. Anlegen & Ändern (billige Schreib-Tools, NUR persistierte Config)
7. `atelier_set_ci` — Style-Anchor, Palette, Default-Modell, Aspect setzen.
8. `atelier_character` — Figur anlegen/ändern/löschen (action: create/update/delete;
   name, description, style_anchor, palette, seed, model). Gibt char_id zurück.
   (Referenzbild-Upload NICHT über Buddy — das ist ein Datei-Upload im Atelier.)
9. `atelier_scene` — Szene anlegen/ändern/löschen/umsortieren (action; description,
   character_ids, dialogues, music-Flag+prompt, camera, location, time_of_day).
10. `atelier_set_screenplay` — Kopf (Titel, Logline, film_model, audio_model,
    voice_model, aspect, default_duration).

### C. Generierung — GESTRICHEN in v1
Bewusst NICHT gebaut (Till-Entscheidung): kein atelier_generate_image /
_generate_music / _make_video / _decompose / _render_film. Der Buddy löst
nichts aus — Generierung + Film bleiben Hand-Aktion im Atelier. (Kann später als
separate Ausbaustufe mit Confirm-Gate kommen, wenn gewünscht.)

## Skill (Anleitung für den Buddy)
Ein Projekt-Skill `atelier-workflow` (write_skill), der dem Buddy beibringt:
- Reihenfolge: erst `atelier_projects`/`atelier_overview` (Kontext holen),
  DANN handeln. Nie blind ins Blaue anlegen.
- Bei Modellwahl: `atelier_models` aufrufen und dem User die passende Liste
  zeigen, statt ein Modell zu raten. Modell nur in CI/Kopf VOREINSTELLEN.
- Prompt-Coaching: mit dem User den Prompt/Steckbrief durchgehen (Szene, Stil,
  Kamera, Charaktere) und als Style-Anchor/Beschreibung PERSISTIEREN.
- Klarheit über Grenzen: der Buddy stellt nur voreinstellt. Das eigentliche
  Generieren/Rendern macht der User im Atelier. Transiente Overlay-Eingaben
  (Bewegungs-Prompt etc.) liefert der Buddy höchstens als kopierbaren Text.
- "Lies mein Atelier": overview + gallery + characters zusammenziehen.

## Offene Design-Fragen (vor dem Bau klären)
1. **Wo leben die Tools?** Im Atelier-Modul (`register(ctx)` registriert sie) —
   so sind sie nur da, wo Atelier installiert ist. (Empfehlung: ja, Modul-Tools.)
2. **project_id-Quelle:** aus `ToolContext.project_id` (aktives Projekt der
   Session). Wenn keins gesetzt → Tool fragt/erwartet explizites Argument.
3. **Granularität:** thematisch gebündelt mit action-Param (atelier_character,
   atelier_scene) statt vieler Einzeltools — Till-Wunsch: gebündelt.

## Nicht in v1
- Buddy generiert/rendert NICHTS (keine Bilder/Videos/Musik/Filme).
- Keine neue Media-Logik — Tools sind dünne Wrapper um vorhandene Atelier-Funktionen.
- Kein Referenzbild-Upload über den Buddy (Datei-Upload bleibt im Atelier).
- Kein Voice/Dialog-Voiceover (das ist E6, separat pausiert).

## Empfohlene Reihenfolge (nur A + B)
1. **Ebene A** (Lese-/Listen-Tools) + Skill-Grundgerüst — Buddy kann Atelier
   "sehen" und Modelle auflisten.
2. **Ebene B** (Anlege-/Voreinstell-Tools) — Buddy baut Charaktere/CI/Drehbuch vor.
3. Skill `atelier-workflow` finalisieren + Grenzen (nichts auslösen) festschreiben.
