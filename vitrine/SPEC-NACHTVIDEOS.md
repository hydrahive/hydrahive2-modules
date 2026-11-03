# Spec: Saisonale Nachtvideos

## Was

Der Nachtmodus der Vitrine erhält neben `dim` und `off` den Modus `video`. Für Frühling, Sommer, Herbst und Winter gibt es getrennte Video-Pools. Innerhalb des aktiven saisonalen Pools rotiert die Vitrine mit dem bestehenden Wechselintervall.

Parallel werden acht Hydra-Schlafvideo-Rezepte vorbereitet: zwei je Jahreszeit. Die Filme folgen verbindlich dem Projekt-Skill `vitrine-video-workflow`.

## Warum

Der bisherige Nachtmodus kann nur eine gedimmte Uhr oder ein schwarzes Bild anzeigen. Till möchte nachts ruhige, sehr dunkle Hydra-Schlafvideos sehen, passend zur meteorologischen Jahreszeit. Die Uhr muss weiterhin lesbar bleiben.

## Konfiguration

```json
{
  "night": {
    "enabled": true,
    "from": "23:00",
    "to": "07:00",
    "mode": "video",
    "videos": {
      "spring": ["hydra-schlaf-fruehling-01.mp4", "hydra-schlaf-fruehling-02.mp4"],
      "summer": ["hydra-schlaf-sommer-01.mp4", "hydra-schlaf-sommer-02.mp4"],
      "autumn": ["hydra-schlaf-herbst-01.mp4", "hydra-schlaf-herbst-02.mp4"],
      "winter": ["hydra-schlaf-winter-01.mp4", "hydra-schlaf-winter-02.mp4"]
    }
  }
}
```

Die Saison folgt wie die vorhandenen Kalenderregeln der meteorologischen Einteilung:

- Frühling: März–Mai
- Sommer: Juni–August
- Herbst: September–November
- Winter: Dezember–Februar

## Verhalten

1. Außerhalb des Nachtfensters bleibt die bestehende Kalenderlogik unverändert.
2. Im Nachtfenster:
   - `off`: schwarzes Bild wie bisher.
   - `dim`: gedimmte Uhr wie bisher.
   - `video`: Video aus dem Pool der aktuellen Saison.
3. Nicht hochgeladene Dateinamen werden ignoriert.
4. Ist der saisonale Pool leer oder keine genannte Datei vorhanden, fällt der Dienst sicher auf `dim` zurück.
5. Mehrere vorhandene Nachtvideos wechseln mit dem bestehenden `rotate_minutes`.
6. Über dem Nachtvideo erscheinen Uhr und Datum. Statusleiste und Meldungskarten bleiben nachts verborgen.
7. Mainboard-Licht behandelt auch den Video-Nachtmodus weiterhin als Nacht.
8. Vorschau, Simulation und Status melden `night="video"` sowie den gewählten Dateinamen.

## Filme

Verbindlich je Clip:

- vertikal 9:16; Ziel 1080×1920, bewährte Generierung 720×1280
- 24 fps, 10 Sekunden, kein Ton, kein Text
- Hydra im unteren Drittel, oberer Bereich ruhig/frei für Uhr
- statische Kamera, keine Schnitte, kein Zoom
- erstes und letztes Bild identisch
- sehr dunkle, ruhige Szene; keine grellen Vollbildblitze
- bekannte fünfköpfige Hydra mit Referenzbild

Motive:

1. Frühling: Moosnest, Kirschblüten, Glühwürmchen
2. Frühling: Farnwiese nach Regen, Sternschnuppe, fernes Wetterleuchten
3. Sommer: Blumenwiese unter Milchstraße und Meteorschauer
4. Sommer: Weide am dunklen See, Glühwürmchen, fernes Gewitter
5. Herbst: Schlafnest aus buntem Laub, langsam fallende Blätter
6. Herbst: dunkler Wald, Mond hinter Wolken, sanftes Wetterleuchten
7. Winter: unter verschneiter Tanne, Schneefall und Polarlicht
8. Winter: geschützte Schneemulde, Eiskristalle und Sternschnuppe

## Akzeptanzkriterien

- Backend akzeptiert und persistiert `night.mode="video"` und vier saisonale Listen.
- Ungültige Saisons oder Videonamen werden abgelehnt.
- Bestehende Konfigurationen ohne `night.videos` laden unverändert mit leeren Pools.
- Der Renderer wählt im Nachtfenster ausschließlich aus dem aktuellen Saison-Pool.
- Rotation, Filtern fehlender Dateien und `dim`-Fallback sind getestet.
- `dim` und `off` verhalten sich unverändert.
- Nachtvideo zeigt Uhr/Datum, aber keine Statusleiste und keine Meldungskarten.
- Cockpit bietet den dritten Modus und Auswahl der hochgeladenen Videos je Saison.
- Deutsche und englische Beschriftungen sind vorhanden.
- Acht Prompt-Archiv-Rezepte sind gespeichert; Rendering bleibt Tills Aktion im Atelier.
