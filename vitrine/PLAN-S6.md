# Plan Vitrine S6 — Chat am Gehäuse

Spec: `vitrine/SPEC-STATUSZENTRALE.md`, Abschnitt S6 (freigegeben 19.10.2026, PR #230). Version 0.12.0.

## 1. Backend `backend/chat.py` (Kern-Weg, testbar mit Fakes)
- `send(user, text, *, handle=router.handle_incoming, busy_dir)`: Text trimmen/prüfen (1–2000), `chat_busy` schreiben,
  `IncomingEvent(channel="vitrine", external_user_id="gehaeuse", target_username=user, sender_name="Gehäuse")`,
  Antwort kürzen (8000), `chat_busy` immer löschen (finally). Fehler: `RuntimeError("Session läuft bereits…")` → Busy.
  Eigener Prozess-Lock: zweite Nachricht während einer laufenden → Busy (ohne Kern-Aufruf).
- `history(user, *, n=20)`: Session per (Buddy, „vitrine“, „gehaeuse“) suchen (nicht anlegen), `list_tail_for_session`,
  nur user (str) / assistant (text-Blöcke), schwärzen (`egress_secrets`), kürzen. Keine Session → [].
- Tests: Event-Felder, Grenzen, Kürzen, Busy (Lock + Kern), chat_busy entsteht/verschwindet (auch bei Fehler),
  Verlauf-Filter (Werkzeug/Reasoning-Blöcke weg), Schwärzung, fremde Session nicht gelesen.

## 2. Routen `backend/kiosk_routes.py`
- `POST /chat` Körper `{text}` (extra=forbid) → `{reply}` | 409 busy | 503 unavailable | 422.
- `GET /chat` → `{"messages": [{role, text}]}`. Über den echten Kern testen (Schlüssel/Adresse/Körper).

## 3. Dienst: nicht zurück zum Video während Hydra antwortet
- `renderer/mode.py`: `chat_busy(data_dir, now)` (Datei frisch < 10 min). `play_dashboard.wants`: busy → idle als 0.
- Tests: busy hält das Dashboard über 2 min; verwaist (> 10 min) zählt nicht; danach 2 min Ruhe → Video.

## 4. Einstellung `chat_enabled` (dash_layout + dashLayout.ts + Schema), Standard true; `/data`-`layout` liefert es.

## 5. Seite `kiosk_page.html` (+ evtl. `kiosk_chat.js` eingebettet über page())
- Chat-Seite als eigene Seite nach den belegten Seiten; Knubbel „Chat“. Verlauf (textContent), Eingabe, Enter/Escape.
- Tippen auf anderer Seite → Chat-Seite, Zeichen ins Feld. „Hydra denkt …“, Eingabe gesperrt; Fehlerzeile.
- Tests (Node-Mini-DOM): Knubbel, Taste springt + Zeichen im Feld, Enter → POST mit Text, Antwort erscheint, 409 →
  Fehlerzeile, kein innerHTML, Chat aus → kein Knubbel. Headless: Layout 1080×1920.

## 6. Cockpit: Schalter „Chat am Gehäuse“ in „Statuszentrale anpassen“.

## 7. Abnahme (braucht BT-Tastatur): Tippen → Antwort, Session getrennt, keine Rückkehr während Antwort.

Gegenprobe: Mutanten für Text-Grenzen, Busy-Lock, chat_busy-finally, Verlauf-Filter, Schwärzung, busy-hält-Dashboard,
Taste-springt, kein innerHTML.
