# Plan Vitrine E3 — Einblendungen: Nachrichten, Fehler, Hydra-Status

Spec: `vitrine/SPEC.md` (Einblendungen, `display_message`, Butler-Aktion; nur Bild, kein Ton).

## Weg einer Einblendung
Backend (im HydraHive-Prozess) schreibt eine Nachricht in eine **Warteschlange als Datei** `<daten>/inbox/<zeit>-<id>.json`
(atomar, eine Datei pro Nachricht). Der Dienst liest den Ordner (max. 1×/s), zeigt, löscht nach Ablauf.
Kein Socket, kein Port – derselbe Weg wie config.json. Funktioniert auch, wenn der Dienst kurz neu startet.

## Nachricht
`{"id", "text" (≤ 280), "title" (≤ 60, optional), "kind": info|success|warning|error, "seconds" (3–600), "created", "source"}`
- `error` ohne `seconds` bleibt 10 min (oder bis zur nächsten Bestätigung im Cockpit)
- höchstens 3 gleichzeitig sichtbar (neueste oben), Rest wartet
- doppelte Nachrichten (gleicher Text + Art innerhalb 60 s) werden zusammengefasst (Zähler „×3“)
- Text: Steuerzeichen raus, Secrets geschwärzt (Kern `redaction.scrub` mit den bekannten Secrets)

## Darstellung (Overlay, unten über der Status-Leiste)
- Karte mit Farbbalken links (Info blau, Erfolg grün, Warnung gelb, Fehler rot), Titel fett, Text bis 3 Zeilen umgebrochen
- Einblenden: 0,4 s hochgleiten + einblenden; Ausblenden: 0,4 s
- Status-Leiste wird bei Hydra-Fehler rot

## Quellen
1. **Agenten-Werkzeug `display_message`** (Modul-Tool, Kategorie vitrine, Standard aus – pro Agent freischalten)
2. **Butler-Aktion `vitrine_message`** („Auf Vitrine anzeigen“: Text mit Vorlagen, Art, Dauer)
3. **Cockpit**: „Testnachricht“ und Liste der aktiven Einblendungen (bestätigen/entfernen)
4. **Hydra-Fehler**: Job alle 30 s → neue Einträge in `errors_log` mit severity error/critical seit letztem Lauf →
   eine Einblendung „Fehler in <Quelle>“ (gedrosselt: max. 1 pro Quelle je 10 min, max. 6 pro Stunde)
5. **Hydra-Status** (Job alle 30 s): laufende Agenten-Läufe (`runner.concurrency.active_count`) → `<daten>/hydra.json`;
   der Dienst zeigt sie in der Status-Leiste („2 Agenten aktiv“)

## Routen
- `POST /messages` (Testnachricht, Admin), `GET /messages` (aktive), `DELETE /messages/{id}` (bestätigen)

## Tests
- `inbox`: schreiben atomar, lesen sortiert, abgelaufene weg, kaputte Datei ignoriert+entfernt, max 3 sichtbar, Zusammenfassen, Ordnergröße begrenzt (max. 100 Dateien, älteste fallen raus)
- `scene`: Karten zeichnen (Farbe je Art, Umbruch, 3 Zeilen max), Animation (Höhe/Transparenz nach Zeit), Leiste rot bei Fehler
- `tool`: Längen, Arten, Dauer-Grenzen, Schwärzung, Ablage
- `butler`: Vorlage `{{message_text}}` wird gerendert, ergibt Einblendung
- `errors`: neue Fehler → Einblendung, Drosselung je Quelle, kein Doppel nach Neustart (Merker-Datei)
- Routen über den echten Kern-Weg (Admin-only)

Abnahme am Gerät: Testnachricht aus dem Cockpit, echter Agent ruft `display_message`, Butler-Flow mit manuellem Auslöser.
