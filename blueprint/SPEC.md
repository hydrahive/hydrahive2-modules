# Blueprint — Visueller Ideen-Editor (Node-Canvas)

> **Stand:** Grundkonzept vom 28.06.2026 (Version 1). Bausteine, Datenmodell und
> Aufbau gelten weiter. Überholt: „kein Agent-Tool nötig“ und „Optional später:
> read_blueprint“. Seit 30.09.2026 gibt es das Tool `blueprint_read`, siehe
> `SPEC-AGENT-READ.md`.

## Problem

Till und der Agent reden bei GUI-/Funktionswünschen aneinander vorbei: Till
beschreibt verbal ("mach die Settings übersichtlicher"), der Agent rät und baut
oft etwas anderes als gemeint. Es fehlt ein **nonverbaler Kanal**, über den Till
Layouts UND Abläufe präzise an den Agenten übergeben kann.

## Lösung (Kurz)

Ein neues Modul **`blueprint`** — ein Node-Canvas wie der Butler-Flow-Editor
(`@xyflow/react` v12), aber als Kommunikations-Werkzeug Till → Agent. EIN
gemeinsames Board mischt **Layout-Bausteine** (Seiten-Design) und
**Flow-Bausteine** (Funktionsplan) frei. Boxen werden beschriftet, frei
angeordnet und über Andockpunkte mit Linien verbunden. Das Board wird als
strukturiertes JSON gespeichert — der Agent liest es als exakten Bauplan
(Knoten + Kanten + Beschriftungen), nicht als bloßes Bild.

## Warum gemeinsames Board (nicht getrennte Modi)

Till will Design und Funktion gleichzeitig skizzieren und nur EINEN Datensatz
übergeben. Baustein-Typen werden farblich unterschieden, nicht in Modi getrennt.

## Baustein-Familien

### Layout-Bausteine (für Seiten-Designs) — Farbe: zinc/neutral
| Typ | Zweck | Beschriftbar |
|-----|-------|--------------|
| `page` | Seiten-Rahmen / Container | Titel |
| `card` | Box / Karteikarte | Titel + Notiz |
| `menu_item` | Menü-Eintrag (Sidebar) | Label |
| `button` | Schaltfläche | Label |
| `input` | Eingabefeld | Label + Platzhalter |
| `toggle` | Schalter | Label |
| `heading` | Überschrift / Text | Text |
| `list` | Liste / Tabelle | Titel |

### Flow-Bausteine (für Funktionspläne) — Farbe: sky/amber/green
| Typ | Zweck | Handles |
|-----|-------|---------|
| `event` | Auslöser (z. B. "Klick auf Button") | Output |
| `action` | Aktion ("mach X") | Input + Output |
| `datasource` | Datenquelle ("hole von Y") | Input + Output |
| `condition` | Wenn/Dann-Verzweigung | Input + true/false-Output |
| `display` | Anzeige ("zeig Z an") | Input |
| `note` | Freitext-Kommentar an den Agenten | — |

Jeder Node: Andockpunkte (`Handle`) links/rechts, frei verbindbar wie Butler.
Layout- und Flow-Bausteine dürfen auf demselben Board frei kombiniert werden
(z. B. ein `button`-Layout-Node, dessen Output-Handle in einen `action`-Flow-Node
führt → "dieser Button macht das").

## Architektur

Modul-Struktur analog zu cryptoboard/scratchpad:
```
blueprint/
  manifest.json          # id, icon "PenTool", nav_group "working"
  backend/
    __init__.py          # register(): router + migrations (KEIN Agent-Tool nötig)
    routes.py            # CRUD der Boards (per-User, ownership-strikt)
    store.py             # DB-Zugriff, ownership-Filter
  migrations/
    001_blueprint.sql    # module_blueprint_boards (id, user, name, graph_json, …)
  frontend/
    index.tsx            # routes + nav + i18n
    BlueprintPage.tsx    # Board-Liste + Editor-Wrapper
    Canvas.tsx           # <ReactFlow> + Drag-Drop + Verbindungen
    NodePalette.tsx      # linke Baustein-Leiste (Layout + Flow, gruppiert)
    nodes.tsx            # Custom-Node-Komponenten je Typ (Handles + Farben)
    PropertiesPanel.tsx  # rechts: Beschriftung/Notiz des selektierten Node
    palette-data.ts      # Baustein-Definitionen (Typ, Label, Default-Felder)
    useBoard.ts          # Nodes/Edges-State, Laden/Speichern (debounced)
    api.ts               # REST-Client
    types.ts
```

Basis: `@xyflow/react` (^12.10.1) ist bereits im Core-Frontend vorhanden
(Butler nutzt es). Kein neuer Dependency.

## Datenmodell

```sql
CREATE TABLE IF NOT EXISTS module_blueprint_boards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT NOT NULL,
    name        TEXT NOT NULL DEFAULT 'Neues Board',
    graph_json  TEXT NOT NULL DEFAULT '{"nodes":[],"edges":[]}',
    created_at  TEXT NOT NULL DEFAULT (...),
    updated_at  TEXT NOT NULL DEFAULT (...)
);
```
`graph_json` = `{ nodes: [...], edges: [...] }` im xyflow-Format, plus pro Node
`data.kind` (layout|flow), `data.subtype`, `data.label`, `data.note`.

## Übergabe an den Agenten

Till sagt im Chat "schau dir Board X an" → der Agent liest das Board via
`GET /api/modules/blueprint/boards/{id}` und interpretiert den Graphen:
- Layout-Nodes → wie die Seite aussehen soll (Hierarchie aus Position/page-card)
- Flow-Nodes + Edges → welcher Ablauf gemeint ist
- `note`-Nodes + Labels → Freitext-Präzisierung

Optional später: ein Agent-Tool `read_blueprint(board_id)` für direkten Zugriff.

## Akzeptanzkriterien

1. Board anlegen/umbenennen/löschen (per-User, fremde unsichtbar).
2. Bausteine per Drag-Drop aufs Canvas, frei verschieben.
3. Andockpunkte verbinden (Linien), Verbindung löschbar.
4. Node selektieren → rechts beschriften (Label + Notiz), Felder je Typ.
5. Auto-Speichern (debounced) ins graph_json.
6. Layout- und Flow-Bausteine auf einem Board mischbar, farblich unterscheidbar.
7. `tsc --noEmit` + `vite build` grün; Backend-Tests grün; alle Dateien < 200 Zeilen.

## Nicht im Scope (v1)

- Kein Code-/Seiten-Generator aus dem Board (Agent liest manuell).
- Keine Echtzeit-Kollaboration.
- Kein Export als Bild (JSON reicht für den Agenten; Screenshot geht via Browser).
- Scratchpad bleibt unangetastet (eigenes Tool, Text/Markdown).
