# Diagramme – Spec

Status: **ENTWURF** – Tills Antworten vom 20.10. eingearbeitet (§11), wartet auf Freigabe.
Stand: 20.10.2026. Anlass: Till fand Archify (github.com/tt-a1i/archify): „sieht saucool aus und ist hyperpraktisch“.
Probe vom 20.10. (nur Arbeitsordner, nichts an HydraHive geändert): `_work/archify-probe/`, Ergebnis
`generated/archify-websuche.html` (Ablauf der Websuche nach Variante C).

---

## 1. Was

Ein HydraHive-Modul **Diagramme** (Modul-ID `diagramme`, Entscheidung Till 20.10.). Damit können Agenten aus einer Beschreibung, einem
Plan oder echtem Code ein **interaktives Diagramm** erstellen: Abläufe, Aufbau eines Systems, Datenbank,
Zustände, Zeitleisten und mehr. Dazu kommt eine **Antwort-Seite** (Ergebnis zuerst, darunter Abschnitte mit Tabellen,
Schritten und Diagrammen).

Das Diagramm
- erscheint **direkt im Chat und ist dort bedienbar** (zoomen, Wege hervorheben, hell/dunkel; Entscheidung Till 20.10.), dazu ein Knopf für das große Fenster,
- landet in einer **Sammlung je Projekt** (Menüpunkt „Diagramme“): wiederfinden, öffnen, als Datei teilen, löschen,
- ist **eine einzige HTML-Datei** ohne Internet (Schrift und Bedienung sind eingebaut),
- verweist je Kasten auf die **Stelle im Code**, wenn es aus einem Repo erstellt wurde.

Grundlage ist **Archify** (MIT, ca. 86.000 Sterne, Version 3.2.0 vom 18.10.2026): eine Anleitung für Agenten
plus ein Node-Hilfsprogramm, das die Beschreibung prüft, die Seite baut und sie in einem echten Browser nachprüft.

## 2. Warum

- Pläne, Befunde und Abläufe kommen heute als lange Textlisten. Ein Diagramm gibt **schneller einen Überblick**
  (Tills Wunsch).
- Wir haben den **Code-Graph** (graphify), aber keine Ansicht für Menschen. Archify kann aus Code ein belegtes
  Diagramm machen.
- **Kostenlos und lokal:** Node und Chromium sind auf jedem HydraHive-Server schon da (Kern-Installer:
  `00-deps.sh` nodejs, `30-python.sh` playwright chromium). Es kostet nur die Tokens des Agenten.

## 3. Befunde aus der Probe (20.10.)

| Punkt | Befund |
|---|---|
| Lauf | `finalize` (Prüfen → Bauen → Nachprüfen → Browser-Prüfung) grün nach 2 Anläufen. Beim ersten Anlauf waren Feldnamen falsch; die Meldung war klar und hat beim Nachbessern direkt geholfen. |
| Abhängigkeiten | Das Hilfsprogramm läuft **ohne** `npm install` (nur Node ≥ 18). Die Browser-Prüfung braucht Chrome: `ARCHIFY_CHROME` auf das Playwright-Chromium setzen, `ARCHIFY_CHROME_NO_SANDBOX=1`. |
| Netz | Einzige Verbindung nach außen ist die Prüfung auf neue Versionen → abschaltbar mit `ARCHIFY_UPDATE_CHECK_DISABLED=1`. Sonst kein Netz. |
| Ergebnis | ~800 KB HTML, 4 eingebettete Skripte, keine externen Quellen, keine Sponsoren-Werbung. Enthält nur Links zum eigenen Repo (Quellen) und zu Archify. |
| Ohne Skripte | Das Diagramm (SVG) ist auch ohne Skripte **vollständig sichtbar**; dann fehlen nur Zoom, Hervorheben, Themen und Export. |
| Sprache | Inhalte frei wählbar (Deutsch geht). Die Bedienleiste gibt es nur in en, zh-CN, zh-TW, es, ko, ar. Eigene Texte über `meta.translations` (486 Schlüssel). |
| Größe Programm | Ordner `archify/` 18 MB, davon 13 MB Beispiele (nicht nötig). Ohne Beispiele etwa 5 MB. |

## 4. Sicherheit (Kern der Sache)

Die Diagramm-Seite ist **von einem Agenten erzeugtes HTML mit Skripten** und deshalb nicht vertrauenswürdig.

- **Nie in der App-Herkunft mit Skripten ausführen.** Anzeige nur in einem `<iframe sandbox="allow-scripts">`
  **ohne** `allow-same-origin`. Damit hat die Seite eine eigene, leere Herkunft: kein Zugriff auf Token,
  Cookies, localStorage oder die API von HydraHive.
- Die App-CSP (`60-nginx.sh`, auf Server-Ebene) erlaubt keine Inline-Skripte. **Gemessen 20.10.** (Chromium, zwei
  CSP-Köpfe auf einer Antwort): App-CSP + eigene CSP → Skript **blockiert**; nur eigene CSP → Skript **läuft**.
  `srcDoc` scheidet aus: Ein srcdoc-Dokument erbt laut HTML-Standard die CSP der App (nicht gemessen).
  → **Kern-Änderung (Till 20.10.: ja):** In `60-nginx.sh` eine eigene `location` für die Ansicht
  (`/api/modules/diagramme/view/`), die **nur** die strenge eigene CSP setzt (nicht die App-CSP) und sonst wie
  `/api/` an den Kern weiterreicht. Migration in `update.sh` (nginx-Konfig neu schreiben + `nginx -t` + reload, bei
  Fehler zurück), Test im Kern wie bei den anderen nginx-Regeln.
- Eigene CSP der Ansicht: `sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; default-src 'none';
  script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none';
  form-action 'none'; frame-ancestors 'self'`, dazu `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`.
  Die Seite kann also **nichts nachladen und nichts senden**; Export (PNG/SVG) läuft über `blob:` im Rahmen.
- **Kein Anmelde-Token in der Rahmen-Adresse:** Die Seite könnte ihre eigene Adresse lesen. Darum holt die App vorher
  einen **Ansichts-Link mit Kurzzeit-Signatur** (HMAC mit eigenem Zweck-Schlüssel, gilt 10 min, nur für dieses eine
  Diagramm und diesen Nutzer). Das Token von HydraHive kommt nie in die Adresse.
- Im Chat: `<iframe sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox">` **ohne**
  `allow-same-origin`, `allow-top-navigation` und `allow-forms`.
- **Kein Netz beim Erzeugen:** `ARCHIFY_UPDATE_CHECK_DISABLED=1`, Hilfsprogramm ohne Netzrechte aufrufen (feste
  Argumente, kein Shell, Zeitgrenze, nur im Arbeitsordner des Moduls).
- Links in der Seite (Quellen auf GitHub) öffnen nur über einen Klick in einem neuen Tab (`allow-popups` +
  `allow-popups-to-escape-sandbox`); keine automatische Weiterleitung, kein `allow-top-navigation`.
- Eingaben vom Agenten (JSON) werden vor dem Lauf auf Größe geprüft (≤ 512 KB) und nur als Datei übergeben.
- Repo-Belege (`--repo-root`) nur aus dem **Arbeitsordner des Projekts** (`safe_path`-Prüfung wie bei den Datei-Werkzeugen).

## 5. Aufbau

```
diagramme/
  manifest.json            id diagramme, default_agent_tools true, nav_group working
  vendor/archify/          feste Kopie von Archify 3.2.0 OHNE examples/, Herkunft + Commit in VENDOR.md, LICENSE (MIT)
  backend/
    __init__.py            register(): Router, Werkzeuge, Skill
    runner.py              ruft node vendor/archify/bin/archify.mjs finalize … (subprocess, Zeitgrenze 180 s)
    store.py               Diagramme je Projekt: data_dir/diagramme/<projekt>/<id>/{candidate.json, bild.html, info.json}
    routes.py              Liste, Ansehen (mit Sandbox-CSP), Herunterladen, Löschen
    tools.py               Werkzeuge für Agenten (§6)
    skill_sync.py          Skill wie mining/backend/skill_sync.py
    locale_de.py           deutsche Texte der Bedienleiste (meta.translations)
  skills/diagramme/SKILL.md   unsere gekürzte, deutsche Anleitung (auf Basis von archify/SKILL.md, Herkunft angegeben)
  frontend/                 Sammlung + Ansicht
  tests/
```

- **Chromium:** Pfad über die Playwright-Installation des Kerns ermitteln (`~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome`),
  in der Admin-Konsole überschreibbar. Fehlt Chromium: Diagramm trotzdem bauen, Browser-Prüfung als „übersprungen“ melden.
- **Node:** Version prüfen (≥ 18). Fehlt Node: klare Meldung in der Sammlung, kein Absturz.
- **Updates von Archify:** nie automatisch. Ein Skript `scripts/vendor-archify.sh <tag>` holt eine neue Version,
  danach laufen die Tests, dann folgt eine eigene Versions-Anhebung mit PR.

## 6. Werkzeuge für Agenten

| Werkzeug | Was |
|---|---|
| `diagramm_erstellen` | Eingabe: `art` (architecture/workflow/sequence/dataflow/lifecycle/erd/class/tree/timeline/waterfall/explainer), `beschreibung` (Archify-JSON bzw. Explainer-Markdown), optional `repo` (Ordner im Projekt für Belege). Führt `finalize` aus. Erfolg → Diagramm in der Sammlung, Rückgabe: Titel, ID, `module_view` für den Chat (§7). Fehler → die **gekürzten Meldungen von Archify** (Code, Pfad, Vorschlag), damit der Agent nachbessern kann. |
| `diagramm_hilfe` | Liefert für eine `art` das Schema und ein Beispiel (aus `vendor/`), damit der Agent nicht raten muss. Auch „welche Art passt?“ (`archify guide`). |
| `diagramm_liste` | Diagramme des Projekts (Titel, Art, Datum), zum Wiederaufnehmen und Ändern. |

- Höchstens **3 Nachbesserungs-Runden** je Auftrag (Skill-Regel), danach dem Nutzer Bescheid geben.
- Die Skill-Anleitung erklärt **wann**: Plan, Ablauf, Architektur, Befund, „zeig mir“ oder „mach mir einen Überblick“.
  Nicht bei jeder Antwort.

## 7. Oberfläche

1. **Im Chat, bedienbar (Till 20.10.):** Liefert das Werkzeug ein Diagramm, zeigt der Chat es als Rahmen
   (Höhe ca. 480 px, im Verlauf mitscrollend) mit Titel, „Groß öffnen“ und „Herunterladen“. Bedienen direkt im Chat.
   - Kern-Änderung nötig (heute kennt der Chat nur Bild, Ton, Video, PDF und EPUB: `runner/_media.py`,
     `MediaPreview.tsx`): neue Art **`diagram`** im Werkzeug-Ergebnis `{kind: "diagram", module: "diagramme",
     id, title}`. Der Chat holt dazu über die Modul-API den signierten Ansichts-Link und zeigt den Rahmen.
     Allgemein gehalten (`kind: "module_view"` mit Modul + ID), damit andere Module (z. B. Recherche-Bericht) es
     später auch nutzen können.
   - Ist das Modul nicht installiert oder der Link abgelaufen: Karte mit Titel und Hinweis, kein leerer Rahmen.
   - Lange Chats: Rahmen erst laden, wenn er ins Bild scrollt (lazy), damit 20 Diagramme nicht alles bremsen.
2. **Sammlung** (Menü „Diagramme“): Kacheln je Projekt mit Vorschaubild, Titel, Art und Datum. Öffnen (Sandbox-iframe,
   Vollbild), Herunterladen (HTML), Löschen (eigener Dialog, kein `confirm()`).
3. Texte Deutsch/Englisch, einfach, ohne Fachwörter („Diagramm“, „Ablauf“, „Aufbau“, „Antwort-Seite“).

## 8. Etappen

| Etappe | Inhalt | Ergebnis |
|---|---|---|
| **K1** (Kern) | nginx-Ausnahme für `/api/modules/diagramme/view/` + Migration; Chat-Art `module_view` (Backend `_media.py`/Dispatcher, Frontend Rahmen mit Lazy-Load). Eigener Kern-PR. | Grundlage für „bedienbar im Chat“. |
| **S1** | Grundgerüst: vendor-Kopie, `runner.py`, `diagramm_erstellen` + `diagramm_hilfe`, Ablage, signierter Ansichts-Link, Route „Ansehen“ mit eigener CSP. Ergebnis als `module_view`. | Agent erstellt ein Diagramm, es ist **im Chat bedienbar**. |
| **S2** | Sammlung im Menü, groß öffnen, herunterladen, löschen, `diagramm_liste`. Vorschaubilder (PNG) für die Kacheln. | Diagramme wiederfinden und teilen. |
| **S3** | Deutsche Bedienleiste (`meta.translations`), gekürzter deutscher Skill, Antwort-Seite (`explainer`). | Alles auf Deutsch. |
| **S4** (optional) | Aus dem Code-Graph (graphify) per Knopf ein Aufbau-Diagramm für ein Projekt. | Überblick über ein ganzes Repo. |

Reihenfolge: K1 und S1 parallel bauen, K1 zuerst mergen (S1 braucht `min_core_version` mit K1). Ohne K1 zeigt S1
statt des Rahmens nur eine Karte mit Link.

Jede Etappe nach dem üblichen Ablauf: Spec-Nachtrag → rote Tests → Code → Mutanten → Gegenprobe →
Version anheben → hydratest → E2E 1600/1280 → PR → CI → Bericht.

## 9. Tests (Auswahl)

- `runner`: feste Argumente, kein Shell, Zeitgrenze, Umgebungsvariablen (Update-Check aus, Chrome-Pfad), Abbruch bei
  > 512 KB, Fehlermeldungen von Archify gekürzt und ohne Pfade außerhalb des Arbeitsordners.
- `routes`: CSP-Kopf exakt, Ansichts-Link: falsche/abgelaufene/fremde Signatur → 404, `X-Content-Type-Options: nosniff`, fremdes Projekt → 404, Pfad-Tricks (`..`) → 404.
- **Kern K1:** nginx-Konfig enthält die Ausnahme genau einmal, setzt dort die App-CSP nicht, `nginx -t` grün;
  Chat zeigt `module_view` als Rahmen mit genau diesen sandbox-Rechten.
- **Sandbox-Test im Browser (E2E):** Ein bösartiges Diagramm versucht `fetch('/api/…')`, `parent.document` und
  `localStorage` zu benutzen → alles scheitert. Das Diagramm selbst bleibt bedienbar.
- `tools`: Erfolg legt genau ein Diagramm an; Fehler legt keins an; `repo` außerhalb des Projekts → abgelehnt.
- Vendor: `VENDOR.md` nennt Version + Commit; `LICENSE` vorhanden; kein `examples/`.
- Ohne Node / ohne Chromium: klare Meldung, kein Absturz.

## 10. Nicht in diesem Modul

- Kein Bearbeiten im Browser per Maus (Archify kann das nicht; Änderungen gehen über den Agenten).
- Kein automatisches Archify-Update.
- Kein Hochladen fremder Diagramm-Dateien in S1–S3 (nur selbst erzeugte).
- Keine Cloud-Dienste (archify.si o. Ä.).

## 11. Entscheidungen Till (20.10.2026)

1. **Name:** „Diagramme“ (Modul-ID `diagramme`).
2. **Wer darf:** alle Agenten – siehe Vorschlag unten (noch zu bestätigen).
3. **Kern-Ausnahme für die Ansicht** (nginx): ja.
4. **Im Chat:** gleich bedienbar → Kern-Etappe K1.

**Zu 2 – wie „alle Agenten“ heute geht (Befund Code):** `default_agent_tools: true` gibt Modul-Werkzeuge nur den
**Master-Agenten** (Buddy) automatisch (`agents/_defaults.py`). Projekt-Agenten und Spezialisten bekommen sie nur, wenn
man sie im Agent-Editor einträgt. Vorschlag:
- `default_agent_tools: true` (Buddy automatisch).
- Im Modul (Admin) ein Knopf **„Für alle Agenten freischalten“**: trägt `diagramm_erstellen`, `diagramm_hilfe`,
  `diagramm_liste` bei allen Agenten ein (mit Sicherung der Agent-Konfigs, rückgängig per zweitem Knopf). Die Werkzeuge
  haben keine Außenwirkung (kein Netz, nur eigener Ablageordner).
