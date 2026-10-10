# VR-Modul (HydraVR)

Verbindet die HydraVR-App auf der Meta Quest 3 mit HydraHive.

## Koppeln per QR (Cockpit → „VR-Brillen“)
1. „Brille koppeln“ → QR erscheint (10 min gültig, einmalig, kein API-Key enthalten).
2. In HydraVR „📷 QR-Code scannen“ → Brille löst den Code ein und bekommt ihren eigenen
   API-Key (Rolle des Nutzers, der den QR erzeugt hat).
3. Gekoppelte Brillen stehen in der Liste; „Entfernen“ widerruft den Key sofort.

QR-Inhalt: `hydravr://pair?s=<server>&c=<code>&p=<sha256//SPKI-Pin oder leer>`. Der Pin wird nur
für lokale Adressen gesetzt (wie im Mining-Modul, `tls_pin.py`). Einlösen: `POST /api/module-device/vr/redeem`
mit Header `X-VR-Pair` (Geräte-Router des Kerns, Rate-Limit). Der QR-Encoder ist eigen (`qr.py`,
`qr_matrix.py`, keine Laufzeit-Abhängigkeit) und wird in den Tests Bit für Bit gegen `qrcode` geprüft.
Agenten können auf der Brille **des eigenen Nutzers**:

| Werkzeug | Wirkung |
|---|---|
| `vr_say(text)` | Brille spricht den Text |
| `vr_notify(title, text)` | Benachrichtigung im HydraVR-Hauptmenü |
| `vr_open_app(app, window?)` | öffnet eine HydraVR-App in einem Büro-Fenster |
| `vr_status()` | ist gerade eine Brille verbunden? |
| `vr_close_window(window)` | schließt ein Büro-Fenster (1–8) |
| `vr_windows()` | welche App liegt in welchem Fenster (Bericht der Brille) |
| `vr_layout(apps[])` | Fenster 1..n mit diesen Apps belegen, übrige leeren |
| `vr_media(action, app?)` | play/pause/stop/next/volume_up/volume_down für Film oder Tonstudio |

Die Brille hört über `GET /api/modules/vr/events` (SSE, Login per API-Key) mit und meldet ihren Fensterstand über `PUT /api/modules/vr/state` (nur im Speicher, nur für den eigenen Nutzer).

**Sicherheit:** Ereignisse gehen nur an Brillen von `ToolContext.user_id`. Kein Zugriff
auf Kamera, Mikrofon oder Dateien. Alles im Speicher, keine Datenbank. Max. 4
Verbindungen je Nutzer, Text ≤ 2000 Zeichen, App-IDs aus fester Liste.

Ist keine Brille verbunden, melden die Werkzeuge das ehrlich an den Agenten
(`success=false`) statt still zu verwerfen.

Tests: `cd vr && python -m pytest -q` (isoliert über `_hh_isolation`).
