# Zieldokument: Agenten-Rechte als Bereiche – „Was darf dieser Agent?“

> **Status:** FREIGEGEBEN (Till, 27.11.2026: E1–E4 entschieden, „ok dann mal los“)
> **Task:** `92b06561`
> **Repo:** Kern `hydrahive2`
> **Spec:** `docs/specs/agent-bereiche.md` · **Plan:** `docs/plans/2026-11-27-agent-bereiche.md` (Kern, PR #789)

Spec und Plan sind verbindlich. Dieses Dokument nennt nur, was je Auftrag abgenommen wird. Bei Widerspruch gilt die Spec.

## Harte Regeln für jeden Auftrag
- **Bereiche sind nur eine Sicht auf `agent.tools`** (E1). Es gibt keine Speicherung als `bereich:x`, und Rechteprüfungen werden nicht verändert.
- **Prompt-Cache bricht nie im Lauf:** Die Tool-Liste an das Modell bleibt innerhalb eines Laufs byte-gleich.
- Bereichsnamen und -sätze wörtlich aus Spec 3.2, in de und en.
- Eigener Worktree unter `_work/wt/bereiche-<n>` (absoluter `cd`). Nach jedem Teilstück committen und pushen. PR auf `main`, **nicht mergen**.
- Lokal nur gezielte Tests. Jeder neue Test muss vor der Änderung rot sein, im Bericht mit Testnamen belegen.
- Keine neue Abhängigkeit. Tests räumen mit `only_own_rows` auf. Dateien bis ca. 200 Zeilen.
- PR-Beschreibung auf Deutsch, ohne @-Mentions.

## Abnahme-Punkte
- **AB1** `agents/areas.py`: 26 Bereiche in 9 Gruppen wie Spec 3.2, `BASE_TOOLS`, `tools_of`. Wächter-Test: Jedes Kern-Tool liegt in genau einem Bereich oder in `BASE_TOOLS`. (Plan-Aufgabe 1)
- **AB2** Manifest-Feld `agent_areas` (Zuordnung oder neuer Bereich, Kern-Bereiche nicht überschreibbar). `all_areas`, `area_of`, `unassigned`. `GET /api/agent-areas`, `unassigned` nur für Admins. (Plan-Aufgabe 2)
- **AB3** Status und Umschalten: `area_states`, `toggle` (fremde Tools bleiben), `GET /api/agents/{id}/areas`, und `agent_tools_forbidden` nennt Bereiche (Plan-Aufgabe 3). Editor-Reiter „Was darf der Agent?“ mit Gruppen, Zeichen, an/aus/teilweise, Expertenansicht zugeklappt, de/en (Plan-Aufgabe 4).
- **AB4** „N neue Werkzeuge – übernehmen?“ erscheint nur bei neu hinzugekommenen Tools eines Bereichs. Ohne Klick ändert sich nichts.
- **AB5** Zweck-Vorschlag: `POST /api/agents/{id}/area-suggestion`, nur Besitzer oder Admin, Ausgabe gefiltert, speichert nichts, Fehler des Modells → leere Liste statt 500. (Plan-Aufgabe 5)
- **AB6** `catalog/auto_pin.py`: höchstens 8, 30 Tage, nur wirksame Tools, beim Laufstart. Die Tool-Liste bleibt im Lauf gleich. (Plan-Aufgabe 6)
- **AB7** Helfer-Schalter setzt den Pool auf die weitergebbaren Bereiche und zeigt, was nicht mitgegeben wird. (Plan-Aufgabe 4)
- **AB8** Admin-Seiten in Bereichssprache: Besitzer-Freigabe, Projekt-Pool, neue Werkzeuge zuordnen, Protokoll (`GET /api/admin/area-audit`). (Plan-Aufgabe 7)
- **AB9** Tests für alles Neue, `tsc` und Frontend-Build grün, PR offen, CI 6/6.
- **AB10** Neue Agenten starten mit `tool_mode: catalog`. Bestand ohne `tool_mode` bleibt `classic`. (Plan-Aufgabe 6)

## Aufträge
| Auftrag | Plan-Aufgaben | Abnahme |
|---|---|---|
| B1 | 1 + 2 | AB1, AB2, AB9 |
| B2 | 3 (Backend) | AB3, AB4, AB9 |
| B3 | 4 (Editor) | AB3, AB4, AB7, AB9 |
| B4 | 5 | AB5, AB9 |
| B5 | 6 | AB6, AB10, AB9 |
| B6 | 7 | AB8, AB9 |
