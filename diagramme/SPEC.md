# Diagramme – Spec

Status: **FREIGEGEBEN** durch Till (20.10.2026), Umsetzung ab K1 + S1.
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
  → **Kern-Änderung K1 (Till 20.10.: ja), allgemein für alle Module:**
  - Ein `<iframe>` kann keinen Anmelde-Kopf schicken, und das Token soll nicht in die Adresse. Die Ansicht läuft
    deshalb über den **Gerätezugang ohne Login** (`ctx.register_device_router`, `/api/module-device/<id>/…`, mit
    Rate-Limit). Das Modul prüft dort eine **signierte Kurzzeit-Adresse** (§4a).
  - nginx bekommt **eine** allgemeine Ausnahme: `location ~ ^/api/module-device/[a-z0-9-]+/sandbox/`. Dort setzt
    nginx **selbst und fest** die Sandbox-CSP (unten) statt der App-CSP, dazu `nosniff`, `Referrer-Policy: no-referrer`,
    `X-Frame-Options: SAMEORIGIN` und `Cache-Control: no-store`. Die Abschottung hängt damit **nicht** vom Modul ab:
    Ein Modul kann sie nur strenger machen, nie lockern.
  - Migration: Marker `hh_module_sandbox` in `update.sh` (wie `hh_peering_tailnet`): fehlt er, wird die
    nginx-Konfig neu geschrieben, `nginx -t`, reload.
  - Mac-Fassung (`modules-mac/60-nginx.sh`) setzt keine App-CSP → dort keine Ausnahme nötig; das Modul setzt die
    Sandbox-CSP zusätzlich selbst (doppelt hält besser, auch beim direkten Zugriff auf Port 8001).
- Sandbox-CSP (nginx fest, Modul zusätzlich): `sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox;
  default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:;
  connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'`.
  Die Seite kann also **nichts nachladen und nichts senden**; Export (PNG/SVG) läuft über `blob:` im Rahmen.
- Im Chat: `<iframe sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox">` **ohne**
  `allow-same-origin`, `allow-top-navigation` und `allow-forms`, `referrerpolicy="no-referrer"`.

### 4a. Signierte Ansichts-Adresse

- Mit Login: `GET /api/modules/diagramme/view-link/{id}` → `{"url": "/api/module-device/diagramme/sandbox/{id}?exp=…&sig=…"}`.
  Nur wenn der Nutzer das Diagramm sehen darf (§5a).
- `sig` = HMAC-SHA256 über `diagramme|view|{id}|{exp}` mit einem aus `settings.secret_key` abgeleiteten Zweck-Schlüssel
  (eigener Kontext-String, nie der Schlüssel selbst). Gültig 10 min. Vergleich zeitkonstant.
- Falsche, abgelaufene oder fremde Signatur, unbekannte ID → **404** (kein Hinweis, was falsch war).
- Die Adresse enthält **kein** Anmelde-Token. Nach Ablauf holt der Chat einfach eine neue (beim Öffnen bzw. Neuladen).

- **Kein Netz beim Erzeugen:** `ARCHIFY_UPDATE_CHECK_DISABLED=1`, Hilfsprogramm ohne Netzrechte aufrufen (feste
  Argumente, kein Shell, Zeitgrenze, nur im Arbeitsordner des Moduls).
- Links in der Seite (Quellen auf GitHub) öffnen nur über einen Klick in einem neuen Tab (`allow-popups` +
  `allow-popups-to-escape-sandbox`); keine automatische Weiterleitung, kein `allow-top-navigation`.
- Eingaben vom Agenten (JSON) werden vor dem Lauf auf Größe geprüft (≤ 512 KB) und nur als Datei übergeben.
- Repo-Belege (`--repo-root`) nur aus dem **Arbeitsordner des Projekts** (`safe_path`-Prüfung wie bei den Datei-Werkzeugen).

## 5a. Alles wird gespeichert (Till 20.10.: „Hauptsache, die Diagramme werden alle gespeichert zum Nachschlagen“)

- **Jedes** erfolgreich erstellte Diagramm wird dauerhaft abgelegt: `data_dir/diagramme/<id>/` mit
  `diagramm.html`, `eingabe.json` (bzw. `.md`), `vorschau.png` (ab S2) und Eintrag in der Tabelle `module_diagrams`
  (Migration): `id, username, project_id, session_id, agent_id, title, kind, created_at, version_of, deleted_at`.
- **Ändern legt eine neue Fassung an**, die alte bleibt: `diagramm_erstellen` mit `ersetzt: <id>` →
  neues Diagramm mit `version_of`. In der Sammlung sieht man die neueste Fassung, die älteren unter „Frühere Fassungen“.
- **Nichts verschwindet von selbst:** keine automatische Löschung, keine Größen- oder Altersgrenze.
- **Löschen nur durch Menschen** (Agenten haben kein Lösch-Werkzeug): erst in den **Papierkorb** (`deleted_at`),
  dort Wiederherstellen oder „endgültig löschen“ (eigener Dialog).
- Abgelegt außerhalb der Projektordner: Wird ein Projekt gelöscht, bleiben seine Diagramme erhalten
  (in der Sammlung unter „ohne Projekt“).
- **Sehen dürfen:** der Nutzer, in dessen Lauf das Diagramm entstand, Admins und Mitglieder des Projekts.
- Gesichert über das normale Backup von `data_dir`.
- Fehlgeschlagene Versuche (Archify meldet Fehler) werden **nicht** als Diagramm gespeichert, nur im Werkzeug-Ergebnis gemeldet.

## 5. Aufbau

```
diagramme/
  manifest.json            id diagramme, default_agent_tools true, nav_group working
  vendor/archify/          feste Kopie von Archify 3.2.0 OHNE examples/, Herkunft + Commit in VENDOR.md, LICENSE (MIT)
  backend/
    __init__.py            register(): Router, Werkzeuge, Skill
    runner.py              ruft node vendor/archify/bin/archify.mjs finalize … (subprocess, Zeitgrenze 180 s)
    store.py               Ablage (§5a): data_dir/diagramme/<id>/ + Tabelle module_diagrams
    links.py               signierte Ansichts-Adresse (§4a)
    routes.py              mit Login: Liste, view-link, Herunterladen, Papierkorb
    device_routes.py       ohne Login: /sandbox/{id} (Signatur prüfen, Sandbox-CSP)
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
     id, title}` – allgemein als **`kind: "module_view"`** mit `module`, `id`, `title`. Konvention für jedes Modul:
     `GET /api/modules/<module>/view-link/<id>` liefert die signierte Adresse. So können später auch andere Module
     (z. B. der Recherche-Bericht) bedienbare Ansichten im Chat zeigen.
   - Das Werkzeug liefert dafür `ToolResult.ok(text, result_type="module_view", module=…, view_id=…, title=…)`;
     der Dispatcher macht daraus `block["media"] = [{"kind": "module_view", …}]`. Nur Modul-IDs, die geladen sind,
     und IDs nach `^[A-Za-z0-9_-]{1,64}$`.
   - Ist das Modul nicht installiert oder der Link abgelaufen: Karte mit Titel und Hinweis, kein leerer Rahmen.
   - Lange Chats: Rahmen erst laden, wenn er ins Bild scrollt (lazy), damit 20 Diagramme nicht alles bremsen.
2. **Sammlung** (Menü „Diagramme“): Kacheln je Projekt mit Vorschaubild, Titel, Art und Datum. Öffnen (Sandbox-iframe,
   Vollbild), Herunterladen (HTML), Löschen (eigener Dialog, kein `confirm()`).
3. Texte Deutsch/Englisch, einfach, ohne Fachwörter („Diagramm“, „Ablauf“, „Aufbau“, „Antwort-Seite“).

## 8. Etappen

| Etappe | Inhalt | Ergebnis |
|---|---|---|
| **K1** (Kern) | allgemeine nginx-Ausnahme `/api/module-device/<id>/sandbox/` mit fester Sandbox-CSP + Marker/Migration; Chat-Art `module_view` (Dispatcher + Frontend-Rahmen mit Lazy-Load, Link über `view-link`). Eigener Kern-PR. | Grundlage für „bedienbar im Chat“. |
| **S1** | Grundgerüst: vendor-Kopie, `runner.py`, `diagramm_erstellen` (inkl. `ersetzt`) + `diagramm_hilfe`, Ablage mit Tabelle (§5a), signierte Adresse (§4a), Sandbox-Route. Ergebnis als `module_view`. | Agent erstellt ein Diagramm, es ist **im Chat bedienbar**. |
| **S2** | Sammlung im Menü (je Projekt, Suche nach Titel), groß öffnen, herunterladen, frühere Fassungen, Papierkorb, `diagramm_liste`. Vorschaubilder (PNG). | Diagramme wiederfinden und teilen. |
| **S3** | Deutsche Bedienleiste (`meta.translations`), gekürzter deutscher Skill, Antwort-Seite (`explainer`). | Alles auf Deutsch. |
| **S4** (optional) | Aus dem Code-Graph (graphify) per Knopf ein Aufbau-Diagramm für ein Projekt. | Überblick über ein ganzes Repo. |

Reihenfolge: K1 und S1 parallel bauen, K1 zuerst mergen (S1 braucht `min_core_version` mit K1). Ohne K1 zeigt S1
statt des Rahmens nur eine Karte mit Link.

Jede Etappe nach dem üblichen Ablauf: Spec-Nachtrag → rote Tests → Code → Mutanten → Gegenprobe →
Version anheben → hydratest → E2E 1600/1280 → PR → CI → Bericht.

## 9. Tests (Auswahl)

- `runner`: feste Argumente, kein Shell, Zeitgrenze, Umgebungsvariablen (Update-Check aus, Chrome-Pfad), Abbruch bei
  > 512 KB, Fehlermeldungen von Archify gekürzt und ohne Pfade außerhalb des Arbeitsordners.
- `links`: Signatur stimmt, abgelaufen/falsch/andere ID → ungültig, zeitkonstanter Vergleich.
- `store`: neue Fassung behält alte; Papierkorb + Wiederherstellen; fremder Nutzer sieht nichts.
- `routes`: CSP-Kopf exakt, view-link nur mit Recht, Sandbox-Route: falsche/abgelaufene/fremde Signatur → 404, `X-Content-Type-Options: nosniff`, fremdes Projekt → 404, Pfad-Tricks (`..`) → 404.
- **Kern K1:** nginx-Ausnahme genau einmal, setzt dort die feste Sandbox-CSP und **nicht** die App-CSP; Marker in
  `update.sh`; Dispatcher reicht `module_view` nur mit gültigen Feldern durch; Chat zeigt den Rahmen mit genau diesen
  sandbox-Rechten, lädt erst beim Hinscrollen und holt bei Fehler einen neuen Link.
- **Sandbox-Test im Browser (E2E):** Ein bösartiges Diagramm versucht `fetch('/api/…')`, `parent.document` und
  `localStorage` zu benutzen → alles scheitert. Das Diagramm selbst bleibt bedienbar.
- `tools`: Erfolg legt genau ein Diagramm an; Fehler legt keins an; `repo` außerhalb des Projekts → abgelehnt.
- Vendor: `VENDOR.md` nennt Version + Commit; `LICENSE` vorhanden; kein `examples/`.
- Ohne Node / ohne Chromium: klare Meldung, kein Absturz.

## 10. Nicht in diesem Modul

- Kein Bearbeiten im Browser per Maus (Archify kann das nicht; Änderungen gehen über den Agenten).
- Kein automatisches Archify-Update.
- Kein Hochladen fremder Diagramm-Dateien in S1–S3 (nur selbst erzeugte).
- Kein Lösch-Werkzeug für Agenten.
- Keine Cloud-Dienste (archify.si o. Ä.).

## 11. Entscheidungen Till (20.10.2026)

1. **Name:** „Diagramme“ (Modul-ID `diagramme`).
2. **Wer darf:** alle Agenten – Vorschlag unten von Till bestätigt („ok mache das so“).
3. **Kern-Ausnahme für die Ansicht** (nginx): ja.
4. **Im Chat:** gleich bedienbar → Kern-Etappe K1.

**Zu 2 – wie „alle Agenten“ heute geht (Befund Code):** `default_agent_tools: true` gibt Modul-Werkzeuge nur den
**Master-Agenten** (Buddy) automatisch (`agents/_defaults.py`). Projekt-Agenten und Spezialisten bekommen sie nur, wenn
man sie im Agent-Editor einträgt. Vorschlag:
- `default_agent_tools: true` (Buddy automatisch).
- Im Modul (Admin) ein Knopf **„Für alle Agenten freischalten“**: trägt `diagramm_erstellen`, `diagramm_hilfe`,
  `diagramm_liste` bei allen Agenten ein (mit Sicherung der Agent-Konfigs, rückgängig per zweitem Knopf). Die Werkzeuge
  haben keine Außenwirkung (kein Netz, nur eigener Ablageordner).

## 12. Etappe S2 im Detail (Stand 20.10.2026, nach S1 live)

S1 ist live (Kern 713754c8, Modul 0.1.0). Till hat das erste Diagramm im Chat gesehen und bedient. S2 macht das
**Nachschlagen** möglich und gibt das Werkzeug **allen Agenten**.

### 12.1 Routen (mit Login, `/api/modules/diagramme/…`)
| Route | Was | Recht |
|---|---|---|
| `GET /list?project=&q=&trash=0\|1` | neueste Fassung je Diagramm-Kette: id, title, kind, project_id, project_name, created_at, versions (Anzahl), agent_name | `can_view` je Zeile |
| `GET /item/{id}` | ein Diagramm + alle Fassungen (id, created_at, agent_name) | `can_view` |
| `GET /download/{id}` | HTML als Datei (`Content-Disposition: attachment`, Name aus Titel), Sandbox-CSP | `can_view` |
| `GET /preview/{id}` | Vorschaubild PNG (siehe 12.3), sonst 404 | `can_view` |
| `POST /trash/{id}` / `POST /restore/{id}` | ganze Kette in den Papierkorb / zurück | Ersteller oder Admin |
| `DELETE /item/{id}` | **endgültig löschen** – nur aus dem Papierkorb, ganze Kette, Dateien weg | Ersteller oder Admin |
| `GET /agents-access` | Anzahl Agenten mit/ohne Werkzeug | Admin |
| `POST /agents-access` `{"on": true\|false}` | Freischalten / Zurücknehmen (12.4) | Admin |

Fehler über `coded()` mit Codes aus `errors.KNOWN` (Fehlerfall immer 404 statt 403, wenn das Diagramm fremd ist).

### 12.2 Seite „Diagramme“ (`/diagramme`, Menü „Arbeiten“)
- Kopf: Suche (Titel), Auswahl Projekt („Alle“, je Projekt, „ohne Projekt“), Umschalter „Papierkorb“.
- Kacheln: Vorschaubild (oder Platzhalter mit Art), Titel, Art in Worten („Ablauf“, „Aufbau“ …), Projekt, Datum,
  „n Fassungen“. Klick → Ansicht.
- Ansicht: großer abgeschotteter Rahmen (Kern-`ModuleViewFrame`-Muster, eigene Kopie im Modul), Knöpfe
  „Herunterladen“, „Frühere Fassungen“ (Liste, Klick zeigt diese Fassung), „In den Papierkorb“.
- Papierkorb: „Wiederherstellen“, „Endgültig löschen“ mit eigenem Dialog („Das Diagramm und alle Fassungen werden
  gelöscht. Das lässt sich nicht rückgängig machen.“) – kein `confirm()`.
- Admin: Kasten „Für alle Agenten“ mit Zahl („12 von 85 Agenten können Diagramme erstellen“) und Knopf
  „Für alle Agenten freischalten“ bzw. „Wieder zurücknehmen“.
- Leer-Zustand: „Noch keine Diagramme. Bitte einen Agenten: „Zeichne mir … als Diagramm.““
- Texte de/en, ohne Fachwörter. Breiten 1600 und 1280 px.

### 12.3 Vorschaubilder
- Beim Erstellen: Chromium (`chrome.find()`) macht ein Bildschirmfoto der HTML-Datei:
  `--headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1200,750 --virtual-time-budget=3000
  --screenshot=<ordner>/vorschau.png file://<ordner>/diagramm.html`. Zeitgrenze 60 s, kein Shell, Umgebung wie runner.
- Kein Chromium oder Fehler → kein Bild (Platzhalter), Diagramm wird trotzdem gespeichert.
- Bestehende Diagramme ohne Bild: beim ersten Abruf von `/preview` nachträglich erzeugen (einmal je Diagramm,
  Fehlversuch wird gemerkt → kein Dauerversuch).

### 12.4 Für alle Agenten freischalten
- Heute bekommen nur Master-Agenten das Werkzeug automatisch (`default_agent_tools`, Kern `agents/_defaults.py`).
- „Freischalten“: für jeden Agenten ohne `diagramm_erstellen` die Werkzeuge `diagramm_erstellen`, `diagramm_hilfe`,
  `diagramm_liste` ergänzen (über `hydrahive.agents.config.update`, also mit Prüfung und atomarem Schreiben).
  Vorher eine **Sicherung**: `data_dir/diagramme/_freischaltung.json` mit der Liste der Agenten, die dadurch neu
  dazukamen (nur IDs, keine Configs).
- „Zurücknehmen“: genau bei diesen Agenten die drei Werkzeuge wieder entfernen (andere bleiben unberührt, auch
  Master mit `default_agent_tools`). Danach Datei leeren.
- Gesperrte oder gelöschte Agenten werden übersprungen, Fehler je Agent werden gezählt, nie Abbruch.
- Agenten, die später neu angelegt werden, bekommen das Werkzeug nicht automatisch (erneut freischalten).

### 12.5 Werkzeug `diagramm_liste`
- Ohne Argumente: die 30 neuesten sichtbaren Diagramme (id, Titel, Art, Datum, Projekt) als Text, zum Wiederaufnehmen
  oder Ändern mit `ersetzt`. Optional `q` (Titel enthält) und `projekt` (nur aktuelles Projekt: `true`).
- Kein Lösch- oder Papierkorb-Werkzeug für Agenten.

### 12.6 Datenmodell
- Migration `002_preview.sql`: Spalte `preview_state TEXT` (`ok` | `fehlt` | `fehler`), Standard `NULL` = noch nie versucht.
- „Kette“ = `id` der ersten Fassung (`version_of` oder `id`). Liste zeigt je Kette die neueste nicht gelöschte Fassung.
- Papierkorb gilt für die ganze Kette (alle Fassungen bekommen `deleted_at`).
