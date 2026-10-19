# Plan Vitrine S2 — Statuszentrale mit Daten

Spec: `vitrine/SPEC-STATUSZENTRALE.md`, Abschnitt S2 (freigegeben 19.10.2026). Nur lesen; einzige Knöpfe bleiben „Zurück“.

## 1. `backend/dash_sources.py` – je Bereich eine Funktion (reine Datenbeschaffung, jede für sich fehlertolerant)
- `message(data_dir)` → neueste sichtbare Karte (aus `renderer.inbox.visible`) oder None
- `hydra()` → Dienst-Zustand, `active_count()`, Fehler der letzten Stunde je Quelle (Anzahl, letzter Text) aus `errors_log`
- `tasks(username)` → Anzahl offen/laufend + Top 5 (Priorität, dann Alter) aus `module_tasks`; Tabelle fehlt → None
- `machine()` → Last, RAM, GPU (aus `renderer.sysinfo`), freier Platz `/`, Laufzeit
- `mining()` → Rechner (Name, an/aus) + €/Tag jetzt aus `module_mining_*` (gleiche Rechnung wie `mining_earnings`); fehlt → None
- Tests: jede Quelle mit Test-DB (Tabellen fehlen, leer, gefüllt), Sortierung der Top 5, Kürzung, Fehler → None statt Ausnahme

## 2. `backend/dash_github.py` – „Wartet auf Till“
- Token aus `hydrahive.projects.config.get(<projekt>)` (`git_repos[*].git_token`, sonst `git_token`), Projekt per Name/ID
- Nur GET, feste URL-Form `https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=20` und
  `/commits/{sha}/check-runs`; `owner/repo` geprüft (`^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`), keine Weiterleitungen,
  Zeitlimit 10 s, Zwischenspeicher 60 s
- Ergebnis je PR: Nummer, Titel (gekürzt, geschwärzt), CI (grün/rot/läuft/keine), mergebar ja/nein, Repo-Kurzname
- Tests mit gefälschtem HTTP-Client: Token kommt nur in den Header, nie ins Ergebnis/Log; Fehler/Timeout → Status-Text;
  falsches Repo-Format wird abgelehnt; nur GET wird benutzt

## 3. `backend/dash_data.py` – Zusammenbau
- `build(data_dir, config)` → festes Schema (pydantic-Modell `DashData`), Texte durch `scrub` + kürzen
- Zwischenspeicher 5 s (lokale Bereiche) bzw. 60 s (GitHub), Thread-sicher
- Tests: Schema vollständig auch wenn alle Quellen fehlen; Secret in Fehlertext/Task-Titel/PR-Titel geschwärzt;
  Zwischenspeicher (zweiter Aufruf innerhalb 5 s fragt Quellen nicht erneut)

## 4. Route + Seite
- `GET /api/module-device/vitrine/data` (Geräte-Router, `kiosk_auth` wie S1)
- `backend/kiosk_page.html` statt der Platzhalter-Seite; Skript lädt `data?k=…` alle 5 s; Zustände: lädt / ok / „HydraHive
  antwortet nicht“; Knopf „Zurück zum Video“; nur `textContent` (kein innerHTML mit Daten)
- Tests: Routen über den echten Kern (Schlüssel, Adresse, 404), Seite enthält keine Daten und kein `innerHTML`

## 5. Cockpit + Config
- `config.json`: `dashboard` = `{"tasks_user": "till", "github_project": "Hydrahive DEV",
  "github_repos": ["hydrahive/hydrahive2", "hydrahive/hydrahive2-modules"]}`; Schema mit Prüfung (Nutzername, Repo-Form)
- Einstellungen-Karte: drei Felder; Statuskarte unverändert
- Tests: Schema-Grenzen, vitest für Anzeige

## 6. Abnahme am Gehäuse (mit Till)
- Maus → Statuszentrale mit echten Werten (Abgleich: Cockpit, Tasks-Seite, Mining-Seite, GitHub-PR-Liste)
- Firefox ruhig < 5 % eines Kerns über 60 s; Backend-Last nicht messbar erhöht

Gegenprobe: Mutanten ohne Bytecode-Cache. Dateien ≤ 200 Zeilen. Version 0.8.0.
