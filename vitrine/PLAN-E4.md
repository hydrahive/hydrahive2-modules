# Plan Vitrine E4 — Abschluss V1

Spec: `vitrine/SPEC.md` (Abschnitt „E4: JPEG-Bildcache“).

## 0. Gerätetest zuerst (vor jedem Code)
JPEG mit Restart-Marker je MCU-Zeile (Pillow `restart_marker_rows=1`, 4:2:0, Q80) an das Display schicken, zusätzlich ein Bild
mit eingesetzten Zeilen. Till schaut aufs Display. Geht das nicht → Stopp, mit Till neu bewerten.

## 1. `renderer/jpegrows.py` – JPEG zeilenweise (reine Funktionen, keine Abhängigkeit außer Pillow)
- `encode(img, quality)` → JPEG mit Restart je MCU-Zeile (MCU-Höhe aus Subsampling: 16 bei 4:2:0)
- `split(jpeg)` → `Rows(head, segments)`; prüft SOI, DRI vorhanden, Anzahl Segmente = Bildhöhe/MCU, sonst `RowsError`
- `join(rows)` → JPEG; RST-Nummern laufen 0–7 zyklisch
- `strip_jpeg(rows, r0, r1)` → JPEG nur dieser Zeilen (SOF-Höhe angepasst), zum Dekodieren des Streifens
- `replace(rows, r0, strip_rows)` → neue Rows mit ersetzten Zeilen
- Tests: Byte-Gleichheit (zusammengesetzt == voll kodiert), Rand-Zeilen (erste/letzte), Bildhöhe kein Vielfaches von 16,
  kaputte/fremde JPEGs (ohne DRI, abgeschnitten, Füllbytes `FF00`, Marker im Datenstrom), RST-Nummern-Folge

## 2. `renderer/framecache.py` – Vorberechnen + Lesen
- Ablage `<daten>/cache/<video>-<hash>.frames/` : `index.json` (Anzahl, w, h, fps, quality, MCU) + `frames.bin` (JPEGs hintereinander)
  + `offsets` im Index. Atomar: erst `.tmp`-Ordner, dann umbenennen. Alte Fassungen derselben Quelle löschen.
- Vorberechnen: ffmpeg → rgb24 → `jpegrows.encode`, **im Hintergrund-Thread mit niedriger Priorität** (`os.nice`), Fortschritt in state.json
- Lesen: `mmap`, liefert Bytes je Bild in Schleife
- Tests: Schlüssel ändert sich bei Quelle/Größe/fps/Qualität; kaputter/halber Cache wird verworfen und neu gebaut; Index passt nicht → verworfen

## 3. Dienst
- `Runner._play`: Wenn Cache fertig → Bildcache-Weg, sonst heutiger Weg (Wechsel beim nächsten Programm-Check)
- Overlay-Bänder (Uhr/Status + Karten) → MCU-Zeilengruppen; nur die neu kodieren. Ohne Bänder → JPEG unverändert senden
- Vorschau aus dem gesendeten JPEG (alle 10 s, wie heute)
- Tests: Bildcache-Weg sendet bei leerem Overlay genau die Cache-Bytes; mit Overlay byte-gleich zu „dekodieren + compose + voll kodieren“;
  Umschalten heutiger Weg → Cache, ohne Lücke; Cache kaputt → zurück zum heutigen Weg, Fehler in state.json

## 4. Einstellungen
- `config.json`: `fps` (12–30, Std. 24), `message_seconds` (5–120, Std. 15); Backend-Schema + Cockpit (SettingsCard)
- Dienst übernimmt fps beim nächsten Programmwechsel (Cache-Schlüssel enthält fps → neue Vorberechnung)
- `inbox.post` nutzt `message_seconds` als Standard (Fehler bleiben 600 s)

## 5. Messung + Abnahme
- CPU über 60 s (Python + Kinder) am Gerät: ohne Einblendung < 10 %, mit Einblendung messen und im PR nennen
- Akzeptanztests mit Till: Rechner-Neustart (Bild ≤ 60 s), USB ab/an, HydraHive-Neustart („Hydra startet“)

Gegenprobe: Mutanten ohne Bytecode-Cache. Dateien ≤ 200 Zeilen.
