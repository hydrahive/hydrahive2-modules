# Task-List-Pagination und kompakte Tool-Ausgabe

## Was

Das Agentenwerkzeug `task_list` liefert standardmäßig höchstens 20 Tasks und unterstützt `limit` (1–100) sowie `offset` (ab 0). Die Antwort enthält `count` als Gesamtzahl der gefilterten Tasks, `returned`, `offset`, `limit`, `has_more` und `next_offset`.

Jeder Listeneintrag enthält nur kompakte Metadaten und höchstens eine kurze Beschreibungsvorschau. Der vollständige Task bleibt über `task_read(task_id=…)` abrufbar. Die HTTP-API und der interne Service behalten ohne Pagination-Argumente ihr bisheriges Vollformat für die bestehende UI.

## Warum

In der 30-Tage-Messung erzeugte `task_list` bei 57 Aufrufen 16.880.145 Ergebnisbytes; 47 Antworten wurden trunkiert. Vollständige Beschreibungen aller Tasks belasten den Modellkontext, obwohl Details meist erst für einen einzelnen Task benötigt werden.

## Wie

- Optionale Pagination im Service, ohne bestehende Aufrufer zu verändern.
- Separate Gesamtzählung mit denselben User-, Status- und Projektfiltern.
- Deterministische Sortierung für stabile Seiten.
- Kompakte Projektion ausschließlich im Agentenwerkzeug.
- Hartes Ergebnisbudget von 40.000 Zeichen; bei besonders breiten Seiten wird die Seite verkürzt und `budget_limited=true` gesetzt.
- Vollständige Details ausschließlich über das vorhandene `task_read`.

## Akzeptanzkriterien

1. Ohne Argumente liefert `task_list` maximal 20 kompakte Tasks.
2. `limit` akzeptiert 1–100, `offset` Werte ab 0.
3. `count` bleibt die Gesamtzahl; `returned`, `has_more` und `next_offset` beschreiben die Seite.
4. Status-, Projekt- und User-Isolation gelten für Liste und Gesamtzahl identisch.
5. Vollständige Beschreibungen erscheinen nicht in `tasks`; `description_preview` ist auf 80 Zeichen begrenzt.
6. `task_read` liefert weiterhin den vollständigen Task.
7. HTTP-API und bestehende Service-Aufrufer bleiben rückwärtskompatibel.
8. Das serialisierte Tool-Ergebnis bleibt unter 40.000 Zeichen; bei Budgetkürzung zeigt `budget_limited=true` den Grund an.
