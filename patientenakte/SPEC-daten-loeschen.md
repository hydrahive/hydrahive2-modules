# Spec: Gesundheitsdaten löschen (Patientenakte)

Status: freigegeben von Till (28.09.2026, „das reicht so grob")

## Warum

Das Modul speichert Gesundheitsdaten (Art. 9 DSGVO), bietet aber nur für
einzelne Akte-Einträge ein Löschen. Apple-Health-Daten, FHIR- und eGA-Importe
und die Akte als Ganzes lassen sich nicht entfernen. Art. 17 DSGVO verlangt,
dass die betroffene Person ihre Daten löschen lassen kann.

Stand vor der Änderung, Live-System:

| Quelle | Tabelle | Umfang |
|---|---|---|
| Apple Health Rohdaten | `health_ingest` | 884 Sätze, 7,65 GB |
| Apple Health Tageswerte | `health_daily` | 6357 Werte |
| FHIR-Import | `fhir_resources` | 327 |
| eGA-Import | `ega_records` | 545 |
| Akte | `akte_patient` + 9 `akte_*`-Tabellen (FK ON DELETE CASCADE) | 1 Akte |

## Umfang

Nur die eigenen Daten des eingeloggten Users (`user_id` bzw. `owner_user_id`).

| Bereich | Was wird gelöscht |
|---|---|
| `apple_health` | `health_ingest` + `health_daily` des Users, optional nur ein Zeitraum |
| `fhir` | alle `fhir_resources` des Users |
| `ega` | alle `ega_records` des Users |
| `all` | alles oben plus die Akte (`akte_patient` → Kind-Tabellen per CASCADE) |

### Zeitraum für Apple Health (`from`, `to`, beide inklusive, `YYYY-MM-DD`)

- `health_daily`: Zeilen mit `date BETWEEN from AND to`.
- `health_ingest`: Ein Rohsatz wird gelöscht, wenn **alle** seine Samples
  (`data.metrics[].data[].date`, Tagesanteil) im Zeitraum liegen. Rohsätze
  ohne Samples zählen über den Tag von `received_at`. Rohsätze, die über die
  Grenze hinausreichen, bleiben stehen und werden im Ergebnis als
  `raw_kept_partial` gemeldet. Sonst würden Tageswerte außerhalb des
  Zeitraums ihre Herkunft verlieren.
- Ohne Zeitraum: alles von Apple Health.

## Nicht im Umfang

- Löschen einzelner Metriken, Rohsätze oder Ressourcen.
- Löschen durch Agenten. Die Agent-Tools bleiben rein lesend. Es gibt
  bewusst **kein** Tool zum Löschen.
- Backups und Snapshots außerhalb der DB.
- `VACUUM`: `secure_delete` ist aktiv, gelöschte Inhalte werden in der
  DB-Datei überschrieben. Die Datei schrumpft aber erst nach einem VACUUM.
  Das bleibt ein Admin-Schritt, weil er die gesamte DB sperrt.
- Der Ingest-Key bleibt bestehen. Wer keine neuen Daten mehr will, muss
  zusätzlich die Automation in „Health Auto Export“ abschalten. Die UI
  weist darauf hin.

## API

`POST /api/modules/patientenakte/data-deletion`, Auth: eingeloggter User.

```json
{ "scope": "apple_health | fhir | ega | all",
  "confirm": "LÖSCHEN",
  "from": "2025-01-01", "to": "2025-12-31" }
```

- `confirm` muss exakt `LÖSCHEN` sein, sonst 400 `confirmation_required`.
  Das ist ein Schutz gegen versehentliche Aufrufe, keine Sicherheitsgrenze.
- `from`/`to` nur bei `apple_health`, beide oder keiner, `from <= to`,
  sonst 422.
- Antwort: Anzahl pro Tabelle, z. B.
  `{"deleted": {"health_ingest": 12, "health_daily": 340}, "raw_kept_partial": 1}`.
- `GET /api/modules/patientenakte/data-deletion/overview` liefert die
  Anzahlen pro Bereich für die UI, plus die Zeitspanne der Apple-Health-Daten.

## Laufzeit

Apple Health wird in Stapeln gelöscht (eine Transaktion pro Stapel), damit
der Schreib-Lock nie lange gehalten wird und parallele Schreiber (Chat,
Ingest) nicht in `database is locked` laufen. Messwerte stehen im PR.

## Protokoll

Log-Zeile ohne Gesundheitsinhalte: User, Bereich, Zeitraum, Anzahlen.

## UI

Neuer Menüpunkt „Daten löschen“ in der Akte: Anzahl pro Bereich,
Zeitraumfelder für Apple Health, pro Bereich ein Button. Bestätigung per
Eintippen von `LÖSCHEN` im Dialog.

## Akzeptanzkriterien

1. Jeder Bereich löscht nur Daten des eigenen Users. Daten anderer User
   bleiben unverändert (Test mit zwei Usern).
2. Zeitraum: Tageswerte außerhalb bleiben, Rohsätze ganz im Zeitraum
   sind weg, Rohsätze über die Grenze bleiben und werden gemeldet.
3. `all` entfernt Akte und alle Kind-Einträge (CASCADE), Importe und
   Apple Health.
4. Ohne korrektes `confirm` wird nichts gelöscht.
5. Ohne Login gibt es 401.
6. Agent-Tools unverändert lesend. Kein neues Tool.
