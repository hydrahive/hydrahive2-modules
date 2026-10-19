# Plan Vitrine S4 — Zuhause + Anordnung

Spec: `vitrine/SPEC-STATUSZENTRALE.md`, Abschnitt S4 (freigegeben 19.10.2026, PR #215). Version 0.10.0.

## 1. Einstellungen `renderer/dash_layout.py` (eine Wahrheit für Server, Dienst, Cockpit-Test)
- `AREAS = messages, home, hydra, tasks, github, machine, mining`; `DEFAULT_ORDER` ohne mining (Mining in „Rechner“).
- `layout_ok(d)` / `normalize(d)`: `order` (bekannte IDs, je höchstens einmal), `hidden` (Teilmenge), `messages_max` 1–5
  (Standard 3), `home_rooms` (Liste ≤ 20 Namen ≤ 60 Zeichen, leer = alle), `mining_in_machine` bool (Standard true).
- Alte S2-Config (`tasks_user`, `github_project`, `github_repos`) wird ergänzt, nicht verworfen.
- `renderer/config.py`: `dashboard_ok` erlaubt die neuen Felder (über dash_layout), `load` ergänzt Standards.
- Tests: Grenzen, Duplikate, unbekannte IDs, alte Config, Zusatzfelder.

## 2. Quelle `backend/dash_home.py`
- Favoriten des Besitzers aus `module_homeassistant_favorites` (Tabelle fehlt → None).
- Entity-IDs prüfen (`^[a-z_]+\.[a-z0-9_]+$`), höchstens 50.
- Ein festes Jinja-Template (IDs als JSON-Liste eingesetzt, keine anderen Eingaben) → JSON je Entity: Name, Raum, Art
  (device_class), Wert, Einheit, Sekunden seit Änderung.
- Aufruf über `sys.modules["hhmod_homeassistant"].client.render_template` (nicht geladen → None), `asyncio.run` (Route
  läuft im Threadpool).
- Gruppieren je Raum: Temperatur, Luftfeuchte, Batterie < 20 %, weiterer Wert; alle weg → `offline_since_h`.
- Raumauswahl (`home_rooms`) filtern. „Sonstiges“ für Favoriten ohne Raum.
- Tests: Template enthält nur geprüfte IDs; Gruppierung; Batterie-Schwelle; offline; Auswahl; Modul fehlt; HA-Fehler.

## 3. Zusammenbau `backend/dash_data.py`
- Neuer Bereich `home` (TTL 60 s), `layout` immer mitgeben (normalisiert), `messages` mit `messages_max`.

## 4. Seite `backend/kiosk_page.html`
- Bereiche nach `layout.order` anordnen (DOM umsortieren), `hidden` ausblenden; Mining als eigene Zeile oder Teil von „Rechner“.
- Bereich „Zuhause“: je Raum eine Zeile (Name links, Werte rechts), grau bei offline, Gelb bei Batterie.
- „Nie zu voll“: nach dem Aufbau von unten ganze Bereiche ausblenden, bis `#unten` in 1920 px passt; Hinweis
  „n Bereiche ausgeblendet (zu voll)“.
- Test (Node-Mini-DOM): Reihenfolge/hidden; Zuhause-Zeilen; Mining in Rechner. Headless-Browser für „zu voll“.

## 5. Cockpit `frontend/DashboardCard.tsx`
- „Statuszentrale anpassen“: Liste mit Schalter + ↑/↓, Einstellungen je Bereich; bestehende Felder (Aufgaben von,
  GitHub) wandern hinein. Räume als Haken (aus `/home-rooms`, Admin-Route liefert die Raumnamen der Favoriten).
- `rules.ts`: `layoutErrors` wie `dash_layout.layout_ok`. vitest.
- Neue Admin-Route `GET /api/modules/vitrine/home-rooms` (nur Raumnamen).

## 6. Abnahme
- Werte gegen HA, Bereich aus/verschieben → Gehäuse ≤ 10 s, volle Seite ohne Überlauf, Firefox < 5 %.

Gegenprobe: Mutanten ohne Bytecode-Cache für ID-Prüfung, Batterie-Schwelle, offline, Reihenfolge, hidden, zu-voll.
