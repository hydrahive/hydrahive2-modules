# Plan Vitrine S5 — Seiten

Spec: `vitrine/SPEC-STATUSZENTRALE.md`, Abschnitt S5 (freigegeben 19.10.2026, PR #219). Version 0.11.0.

## 1. Einstellung `renderer/dash_layout.py` + `frontend/dashLayout.ts`
- `pages`: dict Bereich → 1–3. Voreinstellung messages/home/hydra = 1, tasks/github/machine/mining = 2.
- `layout_ok`: Schlüssel ⊆ AREAS, Werte int 1–3 (kein bool). `normalize`: fehlende Bereiche → Voreinstellung.
- Tests (pytest + vitest): Grenzen, bool, unbekannte Schlüssel, alte Config.

## 2. `/data`
- `layout` bekommt `pages` und `return_seconds` (aus `dashboard_return_seconds`).

## 3. Seite `kiosk_page.html`
- Seite je Bereich aus `layout.pages`; „belegt“ = eingeschaltet und Daten da. Aktuelle Seite merken; nicht belegt → nächste belegte.
- Je Seite anordnen und „nie zu voll“ (S4-Logik) nur über die Bereiche dieser Seite.
- Knubbel: `<nav id="knubbel">` mit Buttons per `createElement`, ● aktuell / ○ andere, ≥ 64 px Klickfläche,
  nur bei > 1 belegten Seiten. Klick → Seite wechseln, sofort neu anordnen (ohne fetch).
- Rückkehr auf Seite 1: letzte Eingabe (mousemove/mousedown/keydown) merken; beim Laden nach `return_seconds`
  ohne Eingabe → Seite 1.
- Tests (Node-Mini-DOM): Voreinstellung zeigt Seite 1 + zwei Knubbel; Klick → Seite 2 ohne fetch; nur eine Seite → keine
  Knubbel; leere gewählte Seite → nächste; nach return_seconds ohne Eingabe → Seite 1; kein Selbstblättern.
- Headless-Browser: Knubbel sichtbar, Klickfläche, nichts läuft über.

## 4. Cockpit `DashboardCard.tsx`
- Je Bereich Auswahl „Seite 1/2/3“, Liste nach Seite gruppiert (Überschrift je Seite). tsc/vitest/eslint.

## 5. Abnahme
- Knubbel ● ○, Klick → Seite 2; Bereich auf Seite 3 → drei Knubbel; nach Video → Seite 1; Firefox < 5 %.

Gegenprobe: Mutanten für Seitengrenzen, Knubbel nur > 1, Klick ohne fetch, Rückkehr auf 1, leere Seite überspringen.
