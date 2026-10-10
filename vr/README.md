# VR-Modul (HydraVR)

Verbindet die HydraVR-App auf der Meta Quest 3 mit HydraHive.
Agenten können auf der Brille **des eigenen Nutzers**:

| Werkzeug | Wirkung |
|---|---|
| `vr_say(text)` | Brille spricht den Text |
| `vr_notify(title, text)` | Benachrichtigung im HydraVR-Hauptmenü |
| `vr_open_app(app, window?)` | öffnet eine HydraVR-App in einem Büro-Fenster |
| `vr_status()` | ist gerade eine Brille verbunden? |

Die Brille hört über `GET /api/modules/vr/events` (SSE, Login per API-Key) mit.

**Sicherheit:** Ereignisse gehen nur an Brillen von `ToolContext.user_id`. Kein Zugriff
auf Kamera, Mikrofon oder Dateien. Alles im Speicher, keine Datenbank. Max. 4
Verbindungen je Nutzer, Text ≤ 2000 Zeichen, App-IDs aus fester Liste.

Ist keine Brille verbunden, melden die Werkzeuge das ehrlich an den Agenten
(`success=false`) statt still zu verwerfen.

Tests: `cd vr && python -m pytest -q` (isoliert über `_hh_isolation`).
