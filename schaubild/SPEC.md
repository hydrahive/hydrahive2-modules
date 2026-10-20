# Schaubild – Spec

Status: **ENTWURF** – wartet auf Tills Freigabe (Fragen in §11).
Stand: 20.10.2026. Anlass: Till fand Archify (github.com/tt-a1i/archify): „sieht saucool aus und ist hyperpraktisch“.
Probe vom 20.10. (nur Arbeitsordner, nichts an HydraHive geändert): `_work/archify-probe/`, Ergebnis
`generated/archify-websuche.html` (Ablauf der Websuche nach Variante C).

---

## 1. Was

Ein HydraHive-Modul **Schaubild** (Modul-ID `schaubild`). Damit können Agenten aus einer Beschreibung, einem
Plan oder echtem Code ein **interaktives Schaubild** erstellen: Abläufe, Aufbau eines Systems, Datenbank,
Zustände, Zeitleisten und mehr. Dazu kommt eine **Antwort-Seite** (Ergebnis zuerst, darunter Abschnitte mit Tabellen,
Schritten und Schaubildern).

Das Schaubild
- erscheint **direkt im Chat** als Vorschau, mit einem Knopf zum Öffnen im großen Fenster,
- landet in einer **Sammlung je Projekt** (Menüpunkt „Schaubilder“): wiederfinden, öffnen, als Datei teilen, löschen,
- ist **eine einzige HTML-Datei** ohne Internet (Schrift und Bedienung sind eingebaut),
- verweist je Kasten auf die **Stelle im Code**, wenn es aus einem Repo erstellt wurde.

Grundlage ist **Archify** (MIT, ca. 86.000 Sterne, Version 3.2.0 vom 18.10.2026): eine Anleitung für Agenten
plus ein Node-Hilfsprogramm, das die Beschreibung prüft, die Seite baut und sie in einem echten Browser nachprüft.

## 2. Warum

- Pläne, Befunde und Abläufe kommen heute als lange Textlisten. Ein Schaubild gibt **schneller einen Überblick**
  (Tills Wunsch).
- Wir haben den **Code-Graph** (graphify), aber keine Ansicht für Menschen. Archify kann aus Code ein belegtes
  Schaubild machen.
- **Kostenlos und lokal:** Node und Chromium sind auf jedem HydraHive-Server schon da (Kern-Installer:
  `00-deps.sh` nodejs, `30-python.sh` playwright chromium). Es kostet nur die Tokens des Agenten.

## 3. Befunde aus der Probe (20.10.)

| Punkt | Befund |
|---|---|
| Lauf | `finalize` (Prüfen → Bauen → Nachprüfen → Browser-Prüfung) grün nach 2 Anläufen. Beim ersten Anlauf waren Feldnamen falsch; die Meldung war klar und hat beim Nachbessern direkt geholfen. |
| Abhängigkeiten | Das Hilfsprogramm läuft **ohne** `npm install` (nur Node ≥ 18). Die Browser-Prüfung braucht Chrome: `ARCHIFY_CHROME` auf das Playwright-Chromium setzen, `ARCHIFY_CHROME_NO_SANDBOX=1`. |
| Netz | Einzige Verbindung nach außen ist die Prüfung auf neue Versionen → abschaltbar mit `ARCHIFY_UPDATE_CHECK_DISABLED=1`. Sonst kein Netz. |
| Ergebnis | ~800 KB HTML, 4 eingebettete Skripte, keine externen Quellen, keine Sponsoren-Werbung. Enthält nur Links zum eigenen Repo (Quellen) und zu Archify. |
| Ohne Skripte | Das Schaubild (SVG) ist auch ohne Skripte **vollständig sichtbar**; dann fehlen nur Zoom, Hervorheben, Themen und Export. |
| Sprache | Inhalte frei wählbar (Deutsch geht). Die Bedienleiste gibt es nur in en, zh-CN, zh-TW, es, ko, ar. Eigene Texte über `meta.translations` (486 Schlüssel). |
| Größe Programm | Ordner `archify/` 18 MB, davon 13 MB Beispiele (nicht nötig). Ohne Beispiele etwa 5 MB. |

## 4. Sicherheit (Kern der Sache)

Die Schaubild-Seite ist **von einem Agenten erzeugtes HTML mit Skripten** und deshalb nicht vertrauenswürdig.

- **Nie in der App-Herkunft mit Skripten ausführen.** Anzeige nur in einem `<iframe sandbox="allow-scripts">`
  **ohne** `allow-same-origin`. Damit hat die Seite eine eigene, leere Herkunft: kein Zugriff auf Token,
  Cookies, localStorage oder die API von HydraHive.
- Die App-CSP (`60-nginx.sh`) erlaubt keine Inline-Skripte. Das Modul liefert die Seite deshalb über eine eigene Route
  mit **eigenem CSP-Kopf**: `sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline';
  style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; form-action 'none';
  frame-ancestors 'self'`. Die Seite kann also **nichts nachladen und nichts senden**.
  - Offen (§11, Frage 3): Gilt der nginx-Kopf auf Server-Ebene zusätzlich zu unserem? Zwei CSPs werden
    beide angewendet (die strengere gewinnt) → die Skripte wären blockiert. Klären in S1 mit einem echten Test hinter nginx.
    Ausweg ohne Kern-Änderung: Ohne Skripte bleibt das Schaubild trotzdem vollständig (§3). Ausweg mit kleiner
    Kern-Änderung: eine nginx-`location` für `/api/modules/schaubild/view/`, die den App-CSP-Kopf **nicht** mitsetzt.
- **Kein Netz beim Erzeugen:** `ARCHIFY_UPDATE_CHECK_DISABLED=1`, Hilfsprogramm ohne Netzrechte aufrufen (feste
  Argumente, kein Shell, Zeitgrenze, nur im Arbeitsordner des Moduls).
- Links in der Seite (Quellen auf GitHub) öffnen nur über einen Klick in einem neuen Tab (`allow-popups` +
  `allow-popups-to-escape-sandbox`, das wird in S1 entschieden); keine automatische Weiterleitung.
- Eingaben vom Agenten (JSON) werden vor dem Lauf auf Größe geprüft (≤ 512 KB) und nur als Datei übergeben.
- Repo-Belege (`--repo-root`) nur aus dem **Arbeitsordner des Projekts** (`safe_path`-Prüfung wie bei den Datei-Werkzeugen).

## 5. Aufbau

```
schaubild/
  manifest.json            id schaubild, default_agent_tools true, nav_group working
  vendor/archify/          feste Kopie von Archify 3.2.0 OHNE examples/, Herkunft + Commit in VENDOR.md, LICENSE (MIT)
  backend/
    __init__.py            register(): Router, Werkzeuge, Skill
    runner.py              ruft node vendor/archify/bin/archify.mjs finalize … (subprocess, Zeitgrenze 180 s)
    store.py               Schaubilder je Projekt: data_dir/schaubild/<projekt>/<id>/{candidate.json, bild.html, info.json}
    routes.py              Liste, Ansehen (mit Sandbox-CSP), Herunterladen, Löschen
    tools.py               Werkzeuge für Agenten (§6)
    skill_sync.py          Skill wie mining/backend/skill_sync.py
    locale_de.py           deutsche Texte der Bedienleiste (meta.translations)
  skills/schaubild/SKILL.md   unsere gekürzte, deutsche Anleitung (auf Basis von archify/SKILL.md, Herkunft angegeben)
  frontend/                 Sammlung + Ansicht
  tests/
```

- **Chromium:** Pfad über die Playwright-Installation des Kerns ermitteln (`~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome`),
  in der Admin-Konsole überschreibbar. Fehlt Chromium: Schaubild trotzdem bauen, Browser-Prüfung als „übersprungen“ melden.
- **Node:** Version prüfen (≥ 18). Fehlt Node: klare Meldung in der Sammlung, kein Absturz.
- **Updates von Archify:** nie automatisch. Ein Skript `scripts/vendor-archify.sh <tag>` holt eine neue Version,
  danach laufen die Tests, dann folgt eine eigene Versions-Anhebung mit PR.

## 6. Werkzeuge für Agenten

| Werkzeug | Was |
|---|---|
| `schaubild_erstellen` | Eingabe: `art` (architecture/workflow/sequence/dataflow/lifecycle/erd/class/tree/timeline/waterfall/explainer), `beschreibung` (Archify-JSON bzw. Explainer-Markdown), optional `repo` (Ordner im Projekt für Belege). Führt `finalize` aus. Erfolg → Schaubild in der Sammlung, Rückgabe: Titel, ID, Pfad der HTML-Datei (Chat-Vorschau, §7). Fehler → die **gekürzten Meldungen von Archify** (Code, Pfad, Vorschlag), damit der Agent nachbessern kann. |
| `schaubild_hilfe` | Liefert für eine `art` das Schema und ein Beispiel (aus `vendor/`), damit der Agent nicht raten muss. Auch „welche Art passt?“ (`archify guide`). |
| `schaubild_liste` | Schaubilder des Projekts (Titel, Art, Datum), zum Wiederaufnehmen und Ändern. |

- Höchstens **3 Nachbesserungs-Runden** je Auftrag (Skill-Regel), danach dem Nutzer Bescheid geben.
- Die Skill-Anleitung erklärt **wann**: Plan, Ablauf, Architektur, Befund, „zeig mir“ oder „mach mir einen Überblick“.
  Nicht bei jeder Antwort.

## 7. Oberfläche

1. **Im Chat:** Liefert das Werkzeug eine `*.schaubild.html`, zeigt der Chat eine Karte mit Titel, kleiner Vorschau
   (Bild) und dem Knopf „Öffnen“ (großes Fenster mit Sandbox-iframe).
   - Heute erkennt der Kern im Chat nur Bild, Ton, Video, PDF und EPUB (`runner/_media.py`,
     `MediaPreview.tsx`). **Etappe S1 ohne Kern-Änderung:** Das Werkzeug liefert zusätzlich ein **PNG-Vorschaubild**
     (Chromium-Bildschirmfoto); das zeigt der Chat schon heute. Dazu ein Link „Im Schaubild-Modul öffnen“.
   - **Später (S4, Kern-PR):** eigene Art `html_sandbox` im Chat.
2. **Sammlung** (Menü „Schaubilder“): Kacheln je Projekt mit Vorschaubild, Titel, Art und Datum. Öffnen (Sandbox-iframe,
   Vollbild), Herunterladen (HTML), Löschen (eigener Dialog, kein `confirm()`).
3. Texte Deutsch/Englisch, einfach, ohne Fachwörter („Schaubild“, „Ablauf“, „Aufbau“, „Antwort-Seite“).

## 8. Etappen

| Etappe | Inhalt | Ergebnis |
|---|---|---|
| **S1** | Grundgerüst: vendor-Kopie, `runner.py`, `schaubild_erstellen` + `schaubild_hilfe`, Ablage, PNG-Vorschau, Route „Ansehen“ mit Sandbox-CSP. **Echter Test hinter nginx** (Frage 3). | Agent kann ein Schaubild erstellen; im Chat erscheint das Vorschaubild; Öffnen im neuen Tab geht. |
| **S2** | Sammlung im Menü, Öffnen im großen Fenster, Herunterladen, Löschen, `schaubild_liste`. | Schaubilder wiederfinden und teilen. |
| **S3** | Deutsche Bedienleiste (`meta.translations`), gekürzter deutscher Skill, Archify-Antwort-Seite (`explainer`). | Alles auf Deutsch. |
| **S4** (Kern) | Anzeige im Chat als echtes, interaktives Schaubild (Art `html_sandbox`), falls Till das will. | Kein Wechsel ins Modul nötig. |
| **S5** (optional) | Aus dem Code-Graph (graphify) per Knopf ein Aufbau-Schaubild für ein Projekt. | Überblick über ein ganzes Repo. |

Jede Etappe nach dem üblichen Ablauf: Spec-Nachtrag → rote Tests → Code → Mutanten → Gegenprobe →
Version anheben → hydratest → E2E 1600/1280 → PR → CI → Bericht.

## 9. Tests (Auswahl)

- `runner`: feste Argumente, kein Shell, Zeitgrenze, Umgebungsvariablen (Update-Check aus, Chrome-Pfad), Abbruch bei
  > 512 KB, Fehlermeldungen von Archify gekürzt und ohne Pfade außerhalb des Arbeitsordners.
- `routes`: CSP-Kopf exakt, `X-Content-Type-Options: nosniff`, fremdes Projekt → 404, Pfad-Tricks (`..`) → 404.
- **Sandbox-Test im Browser (E2E):** Ein bösartiges Schaubild versucht `fetch('/api/…')`, `parent.document` und
  `localStorage` zu benutzen → alles scheitert. Das Schaubild selbst bleibt bedienbar.
- `tools`: Erfolg legt genau ein Schaubild an; Fehler legt keins an; `repo` außerhalb des Projekts → abgelehnt.
- Vendor: `VENDOR.md` nennt Version + Commit; `LICENSE` vorhanden; kein `examples/`.
- Ohne Node / ohne Chromium: klare Meldung, kein Absturz.

## 10. Nicht in diesem Modul

- Kein Bearbeiten im Browser per Maus (Archify kann das nicht; Änderungen gehen über den Agenten).
- Kein automatisches Archify-Update.
- Kein Hochladen fremder Schaubild-Dateien in S1–S3 (nur selbst erzeugte).
- Keine Cloud-Dienste (archify.si o. Ä.).

## 11. Offene Fragen an Till

1. **Name:** „Schaubild“ (Modul-ID `schaubild`) – oder lieber „Überblick“ oder „Diagramme“?
2. **Wer darf:** Werkzeug standardmäßig für **alle Agenten** (`default_agent_tools: true`) oder nur für Projekt-Agenten?
3. **Interaktiv im Browser:** Falls die nginx-Sicherheitsregel die Skripte blockiert (§4): kleine Kern-Änderung
   (eigene nginx-Stelle für die Ansicht) – ok? Ohne Änderung bliebe das Schaubild sichtbar, aber ohne Zoom und Hervorheben.
4. **Chat-Anzeige:** Reicht für den Anfang das Vorschaubild mit Knopf (S1, ohne Kern), oder soll S4 gleich mit?
