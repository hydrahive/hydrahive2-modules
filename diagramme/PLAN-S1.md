# Plan S1 – Diagramme: Grundgerüst, Werkzeuge, Ablage, Ansicht im Chat

Spec: `diagramme/SPEC.md` §4, §4a, §5, §5a, §6. Kern-Voraussetzung: hydrahive2.0 PR #585 (K1, `module_view` +
nginx-Sandbox). Ohne K1 läuft alles außer der Anzeige im Chat (der Text des Werkzeugs nennt dann den Titel).

## Ziel
Ein Agent ruft `diagramm_erstellen` auf → Archify baut und prüft das Diagramm → es wird dauerhaft gespeichert
(mit Fassungen) → der Chat zeigt es bedienbar im abgeschotteten Rahmen.

## Dateien
- `manifest.json` – id `diagramme`, 0.1.0, `default_agent_tools: true`, `min_core_version` = Kern mit K1.
- `migrations/001_diagrams.sql` – Tabelle `module_diagrams` (§5a).
- `backend/__init__.py` – register(): Router, Geräte-Router (Sandbox), Werkzeuge, Migration, Skill.
- `backend/runner.py` – Archify-Aufruf: feste Argumente, kein Shell, Zeitgrenze 180 s, Umgebung (Update-Check aus,
  Chrome-Pfad, no-sandbox), Ein-/Ausgabe nur im eigenen Arbeitsordner, Eingabe ≤ 512 KB, Fehler gekürzt.
- `backend/chrome.py` – Chromium aus der Playwright-Installation finden (überschreibbar per Einstellung).
- `backend/store.py` – Ablage `data_dir/diagramme/<id>/` + Tabelle; Fassungen (`version_of`), Papierkorb, Rechte.
- `backend/links.py` – signierte Ansichts-Adresse (HMAC, Zweck-Schlüssel, 10 min, zeitkonstant).
- `backend/routes.py` – mit Login: `GET /view-link/{id}`, `GET /list` (für S2 vorbereitet, minimal).
- `backend/device_routes.py` – ohne Login: `GET /sandbox/{id}?exp&sig` → HTML mit Sandbox-CSP; sonst 404.
- `backend/tools.py` – `diagramm_erstellen`, `diagramm_hilfe`.
- `backend/errors.py` – Fehlercodes mit Text (`KNOWN`).
- `skills/diagramme/SKILL.md` – deutsche Kurzanleitung (wann, wie, max. 3 Nachbesserungen).
- `frontend/index.tsx` – nur i18n (Seite folgt in S2).
- `tests/` – conftest (Isolation), test_runner, test_store, test_links, test_routes, test_tools.

## Reihenfolge (TDD)
1. Rote Tests für links, store, runner (mit gefälschtem Archify), routes/device_routes, tools → ein Commit.
2. Code je Datei bis grün.
3. Mutanten je Datei.
4. Gegenprobe: neue Tests auf Basis ohne Code rot (Modul ist neu → Import schlägt fehl = rot).
5. Echter Lauf mit echtem Archify + Chromium (Integrationstest, markiert, läuft lokal).
6. hydratest: Kern-Branch K1 + Modul installieren, echter Agent erstellt Diagramm, im Chat bedienbar (E2E 1600/1280).

## Akzeptanz
- Erfolg legt genau ein Diagramm an (HTML + Eingabe + Tabelleneintrag), Fehler legt keins an.
- `ersetzt: <id>` legt eine neue Fassung an, die alte bleibt unverändert.
- Fremder Nutzer: view-link 404; Sandbox ohne/mit falscher/abgelaufener/fremder Signatur 404.
- Sandbox-Antwort mit exakter CSP, nosniff, no-referrer, no-store.
- Archify wird nie mit Shell, nie ohne Zeitgrenze, nie mit Update-Check aufgerufen.
- `repo` nur innerhalb des Projekt-Arbeitsordners.

## Nicht in S1
Sammlung im Menü, Papierkorb-Oberfläche, PNG-Vorschau, `diagramm_liste` (S2); deutsche Bedienleiste, Antwort-Seite (S3);
Knopf „für alle Agenten freischalten“ (S2, Admin-Seite).
