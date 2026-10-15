# Plan Vitrine E1 — Dienst: Video-Schleife, Uhr, Status

Spec: `vitrine/SPEC.md` (freigegeben 15.10.2026). Ziel E1: Nach Modul-Installation zeigt das Gehäuse-Display
dauerhaft ein Video in Schleife mit Uhr/Datum oben und Status-Leiste unten — ohne root, mit Selbstheilung.

## Was der Modul-Installer tut (Kern, gemessen am Code)
- `copy_module_in` → `$HH_DATA_DIR/modules/vitrine/` (Backend, manifest, extension, renderer)
- `has_service: true` → `bash extension/install.sh` **als `hydrahive`** (kein root)
- root-Teile (udev, systemd) wie die Kern-Extensions über `sudo -n bash` (Installer-Regel `hydrahive2-extensions`)

## Dateien
| Datei | Inhalt |
|---|---|
| `vitrine/manifest.json` | id, `has_service: true`, Capability `module.vitrine` admin_only, `persistent_paths` |
| `vitrine/backend/__init__.py` | `register(ctx)`: Router |
| `vitrine/backend/routes.py` | `GET /status` (Dienst aktiv?, Display gefunden?, fps, letztes Video) aus der Status-Datei des Dienstes |
| `vitrine/renderer/aic.py` | Display-Protokoll (finden, GET_PARAMS, RSA-Auth, Frame senden) — eigener Code |
| `vitrine/renderer/artinchip_pub.pem` | öffentlicher Schlüssel (Quelle in UPSTREAM.md) |
| `vitrine/renderer/scene.py` | Overlay zeichnen (Uhr, Datum deutsch, Status-Leiste) — rein, testbar |
| `vitrine/renderer/sysinfo.py` | Last, RAM, GPU-Temp (hwmon amdgpu), Hydra-Dienststatus |
| `vitrine/renderer/video.py` | Video-Auswahl (E1: erstes Video im Ordner, sonst Testbild), ffmpeg-Pipe 1080×1920, Schleife |
| `vitrine/renderer/main.py` | Hauptschleife: verbinden → senden mit Takt → bei USB-Fehler neu verbinden (Backoff); Status-Datei schreiben |
| `vitrine/renderer/requirements.txt` | pyusb, Pillow, cryptography |
| `vitrine/extension/install.sh` | venv (Python wie Kern), udev-Regel `33c3:0e02` → Gruppe hydrahive, systemd-Unit, enable+start |
| `vitrine/extension/uninstall.sh` | Dienst stoppen/entfernen, udev-Regel entfernen (Daten bleiben) |
| `vitrine/UPSTREAM.md` | Protokoll-Quellen + Lizenz-Hinweis |
| `vitrine/tests/` | conftest mit `_hh_isolation`, Tests für scene/sysinfo/video/main/aic (USB gemockt), Manifest |

## Performance-Maßnahmen (gemessen vorher: ~0,8 Kerne bei 30 fps)
- Video beim ersten Start einmal nach `cache/` umrechnen (1080×1920, Ziel-fps, Überblendung am Ende) → Laufzeit nur noch dekodieren
- Overlay nur neu zeichnen, wenn sich der Text ändert (Uhr: 1×/s, Status: alle 5 s); Komposition per `Image.alpha_composite` auf ein vorbereitetes RGBA
- Ziel-fps einstellbar (Standard 30)

## Selbstheilung
- Display weg (USBError/ENODEV) → Ressourcen freigeben, alle 2 s suchen, neu authentisieren
- ffmpeg-Prozess stirbt → neu starten
- systemd `Restart=always`, `RestartSec=3`

## Sicherheit
- Dienst als `hydrahive`, `NoNewPrivileges`, `ProtectSystem=strict`, nur `ReadWritePaths` Modul-Daten
- USB-Zugriff nur per udev auf genau `33c3:0e02`, `MODE=0660 GROUP=hydrahive`
- Route nur mit `module.vitrine`

## Tests (TDD)
1. `scene`: Datum deutsch („Donnerstag, 15. Oktober“), Bildgröße 1080×1920, Text erscheint in oberem/unterem Bereich (Pixelprüfung), Cache (zweiter Aufruf mit gleichem Text = gleiches Objekt)
2. `sysinfo`: liest Fake-`/proc/meminfo`, Fake-hwmon (amdgpu temp1_input), fehlt → kein Absturz
3. `video`: Auswahl (leer → None, sortiert, nur .mp4/.webm/.mkv), Cache-Pfad/Neubau bei geänderter Quelle (mtime/Größe)
4. `aic`: Frame-Kopf exakt (Magic, Länge, frame_id & 0xFFFF), Aufteilung in 256-KiB-Stücke, Auth-Ablauf gegen Fake-Gerät mit Testschlüssel
5. `main`: USB-Fehler → Neuverbinden statt Absturz; Status-Datei geschrieben
6. Manifest: lädt mit Kern-`ModuleManifest`, `has_service` true

Gegenprobe: Mutanten ohne Bytecode-Cache. Abnahme am echten Gerät (Neustart, USB ab/an, CPU-Messung, 24 h).
