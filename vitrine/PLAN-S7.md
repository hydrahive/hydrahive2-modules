# Plan Vitrine S7 — Bluetooth-Geräte koppeln

Spec: `vitrine/SPEC-STATUSZENTRALE.md`, Abschnitt S7 (freigegeben 21.10.2026, PR #247). Version 0.13.0.
Vorprüfung 21.10. auf .2: `dbus-fast` 4.3.0 baut unter Python 3.14 ohne weitere Pakete und liest als Nutzer `hydrahive`
Adapter + gekoppelte Rapoo (`/org/bluez/hci0`, Device1).

## Aufteilung (jede Datei ≤ 200 Zeilen)

| Datei | Aufgabe | testbar ohne Bluetooth? |
|---|---|---|
| `renderer/bt_model.py` | reine Logik: Adresse prüfen, Art aus Icon, Signal-Stufe, **Zwillinge zusammenfassen** (BT3.0/BT4.0), Sortierung, „schwacher Empfang“ | ja (pur) |
| `renderer/bt_jobs.py` | Aufträge aus `inbox/bt-*.json` lesen/prüfen/löschen, Stand `bluetooth.json` atomar schreiben | ja (tmp-Ordner) |
| `renderer/bt_bluez.py` | dünne Schicht auf dbus-fast: Objekte lesen, Adapter-Eigenschaften setzen, Suche an/aus, pair/trust/connect/remove | über Fake-Bus |
| `renderer/bt_agent.py` | `org.bluez.Agent1` (KeyboardDisplay): DisplayPasskey/RequestConfirmation → Stand; Cancel | über Fake |
| `renderer/bt_service.py` | eigener Thread mit asyncio-Schleife: Fenster öffnen/schließen (120 s), Aufträge abarbeiten, Stand alle 2 s, beim Start alles zu | über Fakes |
| `backend/bluetooth.py` | Backend-Seite: Stand lesen (+ veraltet?), Aufträge schreiben, Prüfungen (Adresse, Fenster offen, gesehen) | ja |
| `backend/kiosk_routes.py` | `GET /bluetooth`, `POST /bluetooth/scan`, `POST /bluetooth/pair` (Kiosk) | über den echten Kern |
| `backend/routes.py` | dieselben + `DELETE /bluetooth/{adresse}` (Cockpit, Recht) | über den echten Kern |
| `backend/kiosk_bt.js` | Kiosk-Seite „Bluetooth“ (Liste, Signalbalken, Code groß, kein Entfernen), eingebettet wie `kiosk_chat.js` | Node-Mini-DOM |
| `frontend/BluetoothCard.tsx` | Cockpit-Karte | vitest |
| `renderer/mode.py` | `bt_busy` hält das Dashboard (wie `chat_busy`), verwaist nach 3 min | ja |

## Reihenfolge (TDD: rot → grün → Gegenprobe)

1. **bt_model** – Tests: gültige/ungültige Adressen (Kleinbuchstaben werden groß, `../`, zu kurz), Art je Icon, Signal-Stufen,
   Zwillinge (gleicher Name ohne BT3.0/BT4.0/LE, gleiche erste 3 Bytes → eine Zeile, klassisch zuerst), fremde Geräte mit
   ähnlichem Namen bleiben getrennt, Sortierung (gekoppelt, dann Signal), schwacher Empfang (< −85).
2. **bt_jobs** – Tests: Auftrag nur `scan`/`pair`/`remove` + gültige Adresse, sonst verworfen; älteste zuerst; atomares
   Schreiben (tmp + replace); Stand mit `updated`.
3. **bluetooth.py (Backend)** – Tests: Stand fehlt/alt → `available: false`; pair bei geschlossenem Fenster → `window_closed`,
   nicht gesehen → `not_seen`; scan während offen → Restzeit, kein zweiter Auftrag.
4. **Routen** – Tests über den echten Kern: Kiosk ohne/falscher Schlüssel/fremde Adresse → 404; 422 bei falscher Adresse;
   kein DELETE am Kiosk; Cockpit ohne Recht → 403, mit Recht → Auftrag `remove`.
5. **bt_bluez + bt_agent + bt_service** – Tests mit Fake-Bus: Öffnen setzt Powered/Pairable/Discoverable + Suche + Agent;
   nach 120 s alles zu und Agent ab; beim Dienst-Start alles zu; pair-Reihenfolge klassisch → bei Fehler LE; nach Erfolg
   trust + connect + Meldung „Bluetooth: … gekoppelt“; Code erscheint im Stand und verschwindet nach Ende.
6. **mode.bt_busy** – Test: offenes Fenster hält das Dashboard; > 3 min verwaist zählt nicht.
7. **Kiosk-Seite** – Tests: Knubbel „Bluetooth“ vor „Chat“, Knopf → POST scan, Liste mit Signalbalken, Tippen → POST pair,
   Code groß, **kein** Entfernen-Knopf, kein `innerHTML`, aus (`bluetooth_enabled=false`) → kein Knubbel.
8. **Cockpit-Karte** – vitest: Liste, Entfernen ruft DELETE, Hinweis schwacher Empfang.
9. **Einbau**: `requirements.txt` + `dbus-fast>=4.3,<5`; Dienst startet `bt_service` (Fehler dort stoppen das Display nie);
   `bluetooth_enabled` in dash_layout/Schema/dashLayout.ts; Manifest 0.13.0.
10. **Abnahme am Gehäuse** (Till): Rapoo entfernen (Cockpit) → am Kiosk koppeln → tippen geht; nach 2 min `Pairable: no`.

Gegenprobe (Mutanten): Adress-Regex, Zwillings-Regel, Reihenfolge klassisch→LE, Fenster-Ende, Start-schließt-alles,
window_closed/not_seen, kein Entfernen am Kiosk, bt_busy-Verwaisung.
