# Plan Vitrine S3 — Meldungen mit 24-h-Verlauf

Spec: `vitrine/SPEC-STATUSZENTRALE.md`, Abschnitt S3 (freigegeben 19.10.2026, PR #209). Version 0.9.0.

## 1. Ablage `renderer/inbox.py` (Kern der Änderung)
- Neues Feld `read` (Zeit/None), `KEEP_SECONDS = 24 h`.
- `_all` löscht nichts mehr wegen `expires`, nur Dateien älter als 24 h nach `created` und kaputte Dateien.
- `active()` / `visible()` = Karten fürs Video: `expires > now` **und** ungelesen (Verhalten fürs Video unverändert,
  gelesene verschwinden sofort).
- Neu `recent(data, now)` → `(new, history)`: 24 h, ungelesen bzw. gelesen, neueste zuerst.
- Neu `mark_read(data, id)` → bool; ID nur vergleichen.
- `post`: Zusammenfassen setzt `read = None` (wieder neu). `MAX_FILES` gilt weiter.
- Bestehender Test `test_abgelaufene_verschwinden_und_werden_geloescht` wird zu „verschwindet vom Video, bleibt 24 h“
  (bewusste Änderung laut Spec), plus Test „nach 24 h gelöscht“.
- Tests: Lesen/Verlauf/Zusammenfassen nach dem Lesen/24-h-Grenze/alte Dateien ohne `read`/Pfad-ID.

## 2. Cockpit-Liste `GET /messages`
- Bleibt `inbox.active` (laufende Karten); keine Änderung an Rechten.

## 3. Daten `backend/dash_sources.messages()` + `dash_data`
- Bereich `messages` = `{new: ≤5, new_count, history: ≤10}`; Felder id, title, text, kind, count, time (HH:MM, Ortszeit).
- `message` (S2) entfällt. Schwärzung/Kürzung wie S2. `Builder.invalidate("messages")` nach „Gelesen“.

## 4. Route `POST /read`
- Geräte-Router (`kiosk_auth`), Körper pydantic `{"id": ^[0-9a-f]{12}$}` extra=forbid → sonst 422; unbekannt → 404; 204.
- Tests über den echten Kern: Schlüssel/Adresse/Körper/ID; danach `/data` zeigt die Meldung im Verlauf.

## 5. Seite `kiosk_page.html`
- Bereich „Neu (n)“ mit Volltext + Knopf „Gelesen“ je Meldung, „+ n weitere“; „Verlauf“-Liste; „Keine neuen Meldungen“.
- Klick → `fetch("read?k=…", POST, JSON {id})`, danach sofort neu laden. Nur `textContent`, Knöpfe per `createElement`.
- Test: genau drei `fetch(`-Ziele (data, back, read), weiter kein innerHTML.

## 6. Karte auf dem Video
- `cards.Cards.render(..., hint=bool)`: zweite Zeile „🖱 Maus bewegen für Details“ (Höhe +1 Zeile).
- `main.py`: `hint = state.dashboard == "bereit"`. Test mit Cards (Höhe/Text) und Runner-Zustand.
- Prüfen, ob die Schrift das 🖱-Zeichen kann; sonst „Maus bewegen für Details“ ohne Zeichen (kein Tofu auf dem Display).

## 7. Abnahme
- Meldung aus dem Cockpit → Karte mit Hinweis → Maus → Neu → Gelesen → Verlauf; Firefox < 5 % über 60 s.

Gegenprobe: Mutanten ohne Bytecode-Cache für 24-h-Grenze, gelesen-vom-Video, Zusammenfassen→neu, ID-Prüfung, Hinweis.
