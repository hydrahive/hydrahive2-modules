# Zieldokument: Tool- und Skill-Katalog – kleiner Kern, Rest bei Bedarf

> **Status:** FREIGEGEBEN (Till, 26.11.2026: Design „so ist ok“, Plan „ok passt“)
> **Task:** `2da6ec55`
> **Repo:** Kern `hydrahive2`
> **Spec:** `docs/specs/tool-skill-katalog.md` (Kern, PR #779) · **Plan:** `docs/plans/2026-11-26-tool-skill-katalog.md` (Kern, PR #780)

Spec und Plan sind verbindlich. Dieses Dokument nennt nur, was je Auftrag abgenommen wird. Bei Widerspruch gilt die Spec.

## Harte Regeln für jeden Auftrag
- **Prompt-Cache bricht nie im Lauf** (Spec E4): Die Tool-Liste an das Modell ist innerhalb eines Laufs byte-gleich.
- **`tool_mode` fehlt oder ist `classic`: exakt wie heute** (K7). Bestehende Tests dürfen sich nicht ändern müssen.
- **Rechte erweitern sich nie über den Katalog.** Jede Freigabe läuft über `effective_tool_names`.
- Eigener Worktree unter `_work/wt/katalog-<n>` (absoluter `cd`). Nach jedem Teilstück committen und pushen. PR auf `main`, **nicht mergen** (das macht der Buddy nach dem Review).
- Lokal nur gezielte Tests. Jeder neue Test muss vor der Änderung rot sein, im Bericht mit Testnamen belegen.
- Keine neue Abhängigkeit in `core/pyproject.toml`.
- PR-Beschreibung auf Deutsch, ohne @-Mentions.

## Abnahme-Punkte

### Auftrag 1 – Plan-Aufgabe 1: `effective_tool_names`
- **KA1** `agents/effective_tools.py` mit `effective_tool_names(agent, *, username, project, pool=None) -> list[str]` und `possible_tool_names(agent) -> set[str]`. Die Reihenfolge der Schritte steht in Spec S6.
- **KA2** Der Runner (`runner.py` ~137–143), `_mirror_scope` und `agent_knowledge` nutzen die neuen Funktionen. Für alle bestehenden Agenten ergibt sich dieselbe Tool-Liste wie vorher (Test mit 3 Config-Fixtures).
- **KA3** Tests aus Plan Aufgabe 1 Schritt 1 grün, vorher rot. Die bestehenden Tests laut Plan Schritt 4 sind grün.
- **KA4** PR offen, CI grün, Link im Bericht.

### Auftrag 2 – Plan-Aufgabe 2: `run_tool`
- **RT1** `run_tool` wird in `_runner_tools` als erste Handlung ausgepackt, vor Bestätigung, `vault_gate`, `tool_denied` und `execute_tool`.
- **RT2** Alle 9 Tests aus Plan Aufgabe 2 Schritt 1 (K10/K11) grün, vorher rot.
- **RT3** Argumente werden ohne neue Abhängigkeit geprüft (`check_args`). In `tool_calls` stehen der innere Name und `via` in `metadata`.
- **RT4** PR offen, CI grün.

### Auftrag 3 – Plan-Aufgabe 3: Katalog + `find_tools`
- **KT1** `catalog/` (Index, Suche, Store) und `tools/find_tools.py` laut Schnittstellen im Plan. Der Store läuft auch ohne Postgres.
- **KT2** Die 10 Alltagsanfragen (nur Kern-Tools) liefern mit und ohne Embedding mindestens 9 von 10 Treffern unter den ersten 3.
- **KT3** Gesperrte Tools erscheinen nie im Ergebnis, auch nicht mit Beschreibung. MCP kommt nie in den Katalog, entfernte Tools verschwinden.
- **KT4** PR offen, CI grün.

### Auftrag 4 – Plan-Aufgabe 4: Kategorien + `find_skills`
- **KK1** `catalog/categories.py` mit festem Mapping plus Admin-Bestätigung (Migration 067). `resolve_categories` ist in `effective_tool_names` und `possible_tool_names` eingehängt.
- **KK2** Die Ausschlüsse aus Spec S2 werden nie über eine Kategorie frei (Test je Gruppe), ein nachträglich zugeordnetes Tool ist nicht frei (K12). K15 ist geprüft.
- **KK3** `find_skills` liefert keine fremden Skills, und 5 Anfragen treffen jeweils unter den ersten 3.
- **KK4** PR offen, CI grün.

### Auftrag 5 – Plan-Aufgabe 5: `tool_mode: catalog`
- **KM1** Das Feld `tool_mode` ist da, Standard `classic`. Der Payload eines classic-Agenten ist identisch mit dem vorherigen Stand (Snapshot-Test, K7).
- **KM2** Im catalog-Modus gehen nur Kern ∩ Freigabe, angeheftete und vorgemerkte Tools ans Modell (K1). Die Tool-Liste ist im Lauf byte-gleich, auch mit `run_tool` (K4).
- **KM3** Vorgemerkte Tools wirken erst ab dem nächsten Lauf. Die Obergrenze liegt bei 15, Umschalten mitten in der Sitzung bricht nichts (Review-Fokus 3 und 5).
- **KM4** PR offen, CI grün.

### Auftrag 6 – Plan-Aufgabe 6: Pool, Besitzer-Freigabe, Zuweisung
- **KP1** Migration 068, `agents/tool_pools.py` und die API laut Plan. Ohne Besitzer-Freigabe kann ein Nicht-Admin nichts vergeben (E5).
- **KP2** Alle 10 Tests aus Plan Aufgabe 6 Schritt 1 grün, vorher rot (K5, K13, K14, K16).
- **KP3** `ask_agent` nimmt `tools`/`skills` an: Zuweisung = Anfrage ∩ Pool, sie kommt zu den eigenen Tools dazu. Föderierte Ziele werden mit Fehler abgelehnt.
- **KP4** Oberfläche (de/en) für Agenten-Pool und Besitzer-Freigabe. PR(s) offen, CI grün.

### Auftrag 7 – Plan-Aufgabe 7: Messung
- **KX1** `catalog/metrics.py`, Migration 069 und die Route `GET /api/catalog/metrics` (nur Besitzer oder Admin). Die Tests aus Plan Aufgabe 7 sind grün.
- **KX2** PR offen, CI grün.
