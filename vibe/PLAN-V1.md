# Vibe – Bauplan Etappe V1

> Zur Spec `SPEC.md` (PR #352, Till: „passt“, 4.11.2026). Stand: Plan, **gebaut wird erst nach Tills OK zu diesem Plan.**
> Ablauf je Baustein: rote Tests als eigener Commit → Umsetzung → Mutanten-Gegenprobe → PR mit grüner CI → Tills Merge →
> Abnahme auf hydratest.

## Ziel

Nach V1: Admin klickt **Vibe**, legt ein Projekt an (Name tippen), sieht links den Chat und rechts die laufende
Vite-React-Seite. Nach jeder Antwort entsteht eine Version mit Klartext-Änderung. „Zurück“ geht. Stürzt die App ab,
behebt der Agent den Fehler selbst (höchstens 3 Versuche). Der Container ruht nach 30 Minuten und startet beim Öffnen.

## Gemessen (hydratest, 4.11.2026, Test-Container 2 CPU / 2 GB, Ubuntu 24.04, Pool `dir`)

| Messung | Wert |
|---|---|
| Erstes Anlegen inkl. Image-Download | 10 s, System bereit 17,7 s |
| Wiederstart stop → start → bereit | 1,0–1,2 s (3 Läufe), Stop 0,9 s |
| Node LTS (Tarball, v26.13) installieren | 3,6 s |
| `npm create vite` + `npm install` (react-ts) | 21 s, `node_modules` 96 MB |
| Container auf Platte | 2,3 GB |
| Dev-Server bis erste Antwort | 1,6 s, RAM im Leerlauf 215 MB |
| Server → Container:5173 | HTTP 200, HMR-WebSocket 101 |
| Vite mit fremdem `Host`-Kopf | **403** → `server.allowedHosts` nötig |
| Node aus Ubuntu 24.04 (apt) | v18, `npm create vite` scheitert (`styleText`) → Node LTS selbst holen |
| 10-GiB-Grenze (`-d root,size=10GiB`) | **wirkt nicht** auf dem `dir`-Pool (`df` im Container: 17 T) |

**Nicht gemessen** (siehe „Nicht gemessen“ unten): ACL-Abschottung für Vibe, Kostengrenze je Fehler-Lauf, Browser-Fehler.

## Entscheidungen aus dem Lesen des Codes

1. **Bausteine werden kopiert, nicht importiert.** Der Kern lädt jedes Modul mit `spec_from_file_location` unter
   eigenem Namen (`modules/loader.py`). Ein `import hydralabor.backend…` aus Vibe wäre nicht verlässlich. Kopiert und
   für Vibe angepasst werden: `incus.py`, `network.py`, `container.py` (Muster), `probe_auth.py`, `probe_site.py`.
   Ein späteres Zusammenlegen im Kern ist eine eigene Aufgabe, nicht Teil von V1.
2. **Eigener Netz-Name `hhvibe0` und eigene ACL `hhvibe-acl`**, nicht das Netz des Labors. Beide Module dürfen nebeneinander
   laufen, keines räumt das Netz des anderen ab. Teilnetz-Auswahl wie im Labor, mit anderen Kandidaten
   (`10.79.0.0/24`, `10.80.0.0/24`, `172.31.79.0/24`), damit es keine Überschneidung gibt.
3. **Ende eines Agenten-Zugs erkennt das Modul über einen Poller (`ctx.register_job`), nicht über den Event-Bus.**
   *Geändert 5.11. nach Lesen des Kerns (Baustein 6).* Der Event-Bus (`runner/event_bus.py`) eröffnet für jeden Lauf einen
   **frischen Kanal** (`bus.open(session_id)` in `start_run_task`); ein Hörer, der vorher angehängt wurde, bleibt am alten
   Kanal hängen und hört nichts (gemessen: Hörer vor `open()` bekommt 0 Ereignisse, nach `open()` alle). Ein Dauer-Hörer
   wäre also nur über Wiederanhängen nach jedem Lauf möglich – und `register_job` ist der dafür vorgesehene, vom
   Kern überwachte Weg. Darum: alle 2 s `is_running(session_id)` je aktivem Vibe-Projekt; Wechsel „läuft → läuft nicht“
   = Zug zu Ende → genau eine Version speichern. Zustand je Projekt im Speicher; nach Neustart startet jedes Projekt als
   „läuft nicht“, ein unterbrochener Zug erzeugt dann beim nächsten Wechsel höchstens eine zusätzliche Version.
   Vorteil: kein Verlust beim Wiederverbinden, keine doppelten Versionen, nichts hängt am Bus.
4. **Chat links = `ChatPane` des Kerns**, wie Legal (`CaseChat.tsx`) und Storyteller (`ChatDock.tsx`):
   `<ChatPane deepLinkSid projectId showSidePanels={false} preferredAgentId agentSelectionExplicit />`. Kein eigener Chat.
   Sitzung mit `metadata.embedded_in = "vibe"`, damit das Projekt-Cockpit sie nicht von selbst öffnet.
5. **Platzgrenze durch das Modul**, weil `size=` auf `dir` nicht greift: Vor jeder Agenten-Runde und nach dem Zug
   misst das Modul `du -s /work` im Container (fest eingetragener Befehl). Über der Grenze (Vorschlag **5 GB**, aus 2,3 GB
   gemessen + Luft) wird der Agent angehalten und im Chat steht, was zu groß ist. Zusätzlich `ulimit`-freie Sperre:
   Ein Agent, der trotzdem füllt, trifft die Grenze des Hosts, nicht der des Containers. **Das Risiko bleibt deshalb
   offen**; echter Schutz wäre ein Pool-Typ mit Quota (btrfs/zfs/lvm) und gehört in den Task „Server-Hardware“
   (`4d03dde2`).
6. **Zeitmaschine über Git im Container**, `git` als Nutzer `vibe` (UID 1000), Commit nach jedem Zug durch das Modul,
   nicht durch den Agenten (der könnte es vergessen oder die Historie umschreiben). Befehle sind feste Skripte,
   Eingaben nur als Argument. `git config` im Projekt: `user.name=Vibe`, `core.hooksPath=/dev/null`.
7. **Vorschau-Anmeldung per Ticket in der Adresse, nicht per Cookie des Labors.** Das Labor setzt `hh_labor_probe`
   (HttpOnly, SameSite=Strict) auf `:8443`; Cookies trennen nicht nach Port. Für das iframe gilt aber SameSite=Strict
   als „anderer Kontext“, das Cookie würde dort **nicht** mitgeschickt (Browserverhalten, hier nicht getestet).
   Deshalb: `POST /api/modules/vibe/preview/open` (Admin) gibt ein **Einmal-Ticket** (60 s), die Seite setzt es als
   `src` des iframes (`…:8444/__vibe_login?t=…`), die Durchreiche löst es ein und leitet auf einen **Pfad mit Token**
   (`/__t/<token>/`) weiter. **Entschieden 5.11. nach Messung: Token im Pfad, kein Cookie** (siehe „Gemessen“ unten).

   **Gemessen (5.11.2026, Chromium 153 über Playwright, zwei Ursprünge mit eigenem TLS, iframe mit
   `sandbox="allow-scripts allow-forms"`, je Verfahren 3 Durchläufe, alle drei gleich):**

   | Verfahren | Vorschau im iframe lädt | WebSocket (HMR-Ersatz) im iframe |
   |---|---|---|
   | Cookie `SameSite=Strict` | ja | **Fehler** (Cookie wird nicht gesendet) |
   | Cookie `SameSite=None; Secure` | ja | ok |
   | Cookie `SameSite=None; Secure; Partitioned` | ja | **Fehler** |
   | **Token im Pfad** | ja | **ok** |

   Dazu gemessen: (1) Die Seite im sandbox-iframe **kann weder `sessionStorage` des Elternfensters noch ihr eigenes
   Storage oder `document.cookie` lesen** (`SecurityError`); der Login-Token von HydraHive ist von dort aus nicht
   erreichbar. (2) Eine **fremde Seite** (anderer Ursprung als `frame-ancestors` erlaubt) kann die Vorschau **nicht**
   einbetten, auch nicht mit gültigem Token im Pfad (Chromium zeigt `chrome-error`). (3) Das Top-Level-Öffnen mit Token
   im Pfad funktioniert. **Nicht gemessen:** WebSocket durch **nginx** mit `auth_request` (hier nur ohne nginx
   gemessen – das kommt in der Probe auf hydratest), Firefox und Safari (nur Chromium getestet), ob ein Token im Pfad in
   Zugriffsprotokollen von nginx landet (ja: es steht im Pfad; Protokoll für diesen Port ausschalten oder maskieren).
   **Folge:** Cookie `SameSite=Strict` scheidet aus (bricht HMR), `Partitioned` ebenfalls; `SameSite=None` würde gehen,
   hängt aber an Cookie-Trennung nach Port (Cookies trennen nicht nach Port: ein Cookie von :8444 ginge auch an :8443
   und :443). Token im Pfad hat dieses Problem nicht.
8. **nginx-Datei und Port brauchen root.** Das Labor schreibt seinen Block über `sudo -n bash -c <fester Text>`
   (`probe_site.py`, Muster Radiostream/Installer-Regel); Vibe übernimmt genau diesen Weg, keine zusätzlichen
   Rechte. Ohne `sudo -n` steht in der Oberfläche eine klare Meldung, die Vorschau fehlt, das Modul bricht nicht ab.
   **Eigener Port 8444**, Labor nutzt 8443. Gleiche nginx-Struktur, eigene Datei `/etc/nginx/hh-vibe-preview.conf`,
   eigener `proxy_cache`-Name. Header: **kein** `X-Frame-Options`, dafür `frame-ancestors https://<Adresse von HydraHive>`
   (aus dem `Host` der Anfrage, geprüft mit der `_HOST`-Regel aus `probe_auth.py`).
9. **Vite-Vorlage fest im Modul** (`vibe/template/`), kein `npm create` zur Laufzeit: schneller, wiederholbar, und
   `allowedHosts: true` + Meldeskript sind schon drin. Abhängigkeiten sind gepinnt (`package.json` + Lockfile). Die
   Installation beim Anlegen: `npm ci`.
10. **Meldeskript für Browser-Fehler steckt in der Vorlage**, nicht in der Durchreiche (nginx kann HTML nicht sicher
    umschreiben). Der Agent kann es theoretisch löschen. Dagegen: Das Modul prüft vor jedem Zug per `grep`, ob
    `vibe-report.js` noch eingebunden ist, und legt es sonst still wieder an (Hash-Vergleich der Datei).

## Dateien

```
vibe/
  manifest.json              id vibe, Version 0.1.0, nav_group working, capability module.vibe (admin_only)
  SPEC.md  PLAN-V1.md
  agent/PROMPT.md            Systemprompt des Vibe-Agenten
  skills/vibe-regeln/        Skill: VIBE.md-Format, kurze Schritte, Fehlerbehebung
  template/                  Vite + React + TS, gepinnt, vibe-report.js, VIBE.md-Vorlage, vite.config.ts
  migrations/001_vibe.sql    Tabelle module_vibe_projects, module_vibe_versions
  backend/
    __init__.py              register(): Migrationen, Router, Geräte-Router (Vorschau-Login), Skill, Aufräumen beim Start
    incus.py                 kopiert aus hydralabor, Name/Pfade angepasst
    network.py               hhvibe0 / hhvibe-acl
    container.py             Namen hh-vibe-<id>, Limits, launch, ruhen/wecken
    provision.py             Schritte: user, packages, node (LTS-Tarball), vorlage, git, npm ci, links
    projects.py              anlegen/entfernen (Kern: project_config, execution.set_container, _managed)
    agent_profile.py         Werkzeuge = K1-Allowlist ohne fetch_url, Skills, Prompt
    versions.py              git commit/log/diff --stat/restore/revert, Klartext-Zusammenfassung
    guard.py                 Platzgrenze (du), VIBE.md-Prüfung, Meldeskript-Prüfung
    watcher.py               Event-Bus-Hörer je Sitzung (+ Rückfall Abfrage), ruft versions + heal
    heal.py                  Fehler → Agentenlauf, 3 Versuche, gleicher Fehler 2× = Abbruch, Kostengrenze
    preview_auth.py          Ticket + Pfad-Token (Muster probe_auth.py)
    preview_site.py          nginx-Block :8444, frame-ancestors
    idle.py                  Leerlauf-Wächter: 30 min ohne Anfrage → stoppen
    routes.py  routes_preview.py
  frontend/
    index.tsx  VibePage.tsx  ProjectPicker.tsx  Timeline.tsx  DiffView.tsx  PreviewFrame.tsx  api.ts  i18n.ts  logic.ts
  tests/
    _hh_isolation.py (byte-gleich), conftest.py, fake_incus.py, fake_git.py, test_vibe_*.py
```

Alle Dateien ≤ 200 Zeilen (Regel des Repos). Texte de/en. Kein `print()`, keine festen Pfade (über Einstellungen).

## Bausteine (Reihenfolge, jeweils rote Tests zuerst)

### 1. Gerüst und Zugriff
- Rot: Manifest gültig; Capability `module.vibe` Standard `admin_only`; Migration legt beide Tabellen an; Nicht-Admin
  bekommt 403; ohne `incus` (`incus.available()` falsch) meldet die Seite `vibe_no_incus`, legt nichts an.
- `manifest.json`, `migrations/001_vibe.sql`, `backend/__init__.py`, `routes.py` (nur `GET /state`), `incus.py`.
- Eintrag in `hub.json`. `scripts/check_version_bump.py origin/main` und `check_test_safety.py` grün.

### 2. Netz und Container
- Rot (mit `fake_incus`): `ensure_network` legt ACL, Netz, Bindung an und doppelt nichts an; Teilnetz-Wahl überspringt
  belegte; `launch` nutzt `--no-profiles`, Pool aus Profil `default`, Limits aus Einstellungen; ruhen/wecken; Name
  `hh-vibe-<id>` passt zu `^[a-z][a-z0-9-]{1,62}$`; zwei Projekte → zwei Container, ein Netz.
- `network.py`, `container.py`. **Echte Probe vor dem PR** auf hydratest: Container erreicht Internet (apt/npm), **nicht**
  den Server, das Gateway, den Router und das Heimnetz. Zieladressen ausdrücklich **nicht** `192.168.178.1` und `.3`
  (Tills Regel); stattdessen die eigene Adresse des Servers und eine freie Adresse im Heimnetz.

### 3. Einrichtung im Container
- Rot: Schritte laufen in fester Reihenfolge, jeder mit `report(key)`; Fehler in einem Schritt → `SetupError` mit
  Schritt-Name; Node kommt als **Tarball der aktuellen LTS** (nicht per `apt`); Vorlage landet in `/work` als Nutzer
  1000; `git init` mit Erst-Commit „Start“; `npm ci` läuft als Nutzer, nicht als root; kein Token in der Umgebung.
- `provision.py`, `template/`. Dauer wird gemessen und im PR genannt (Erwartung nach Messung: etwa 40 s ohne Image-Download).

### 4. Projekt und Agent
- Rot: `projects.create` legt Projekt + Agent an, setzt `execution=container` (K1), Werkzeuge = Allowlist, `managed_by=vibe`;
  Nutzer kann Werkzeuge/Prompt/Projekt des Agenten **nicht** ändern (Kern lehnt ab), das Modell schon; Fehler mittendrin
  räumt das Projekt wieder ab (Muster `lab_project.create`); `remove` löscht nur Projekte mit der Vibe-Markierung.
  **Gegenprobe:** Ein fremdes (nicht von Vibe angelegtes) Projekt bleibt unverändert, `set_container` wird dafür nie
  aufgerufen.
- `projects.py`, `agent_profile.py`, `agent/PROMPT.md`, `skills/vibe-regeln/`.

### 5. Zeitmaschine
- Rot: Commit nach einem Zug enthält alle Änderungen; Kurztext = erste Zeile der Agenten-Antwort, höchstens 100 Zeichen,
  Steuerzeichen/Zeilenumbrüche entfernt; `diff --stat` wird zu „N Dateien geändert“ (Klartext, ohne Git-Wörter);
  `restore(v)` erzeugt eine **neue** Version mit dem Stand von `v`, keine Version geht verloren; `revert(v)` bei Konflikt
  bricht ab, `/work` bleibt unverändert, Meldung „hängt mit späteren Änderungen zusammen“; Dateien über 2 MB und
  `node_modules` kommen nicht in die Versionen (`.gitignore` aus der Vorlage, vom Modul erzwungen).
- `versions.py`. Git-Aufrufe nur als Argumentliste im Container (`incus exec … -- git …`), nie in einer Host-Shell.
  **Das Zusammenspiel `revert` bei Konflikt ist nicht gebaut und nicht getestet** – dieser Baustein ist der Test.

### 6. Hörer und Fehlerbehebung — **umgesetzt (5.11.), echte Probe auf hydratest**
- **Gebaut:** `watcher.py` (Poller alle 2 s, genau eine Version je Zug, kein Doppel, nachgeholt nach Fehlschlag),
  `heal.py` (3 Versuche, gleiche Meldung 3× in Folge bricht ab, Gesamtdecke 250 000 Tokens, Schalter, ein Lauf je
  Projekt, Meldung als Zitat), `heal_run.py` (Lauf in derselben Sitzung, Kostengrenze 100 000 Tokens je Lauf zwischen
  zwei Runden, Zeitgrenze 3 min), `jobs.py` (Anlegen + Einrichten mit Fortschritt, „Nochmal versuchen“ ab Fehlerschritt),
  `chat.py` (dünne Hülle um die Kern-Sitzung), Migration `002_progress.sql`.
- **Die Probe hat drei Fehler gefunden, alle behoben:** (1) `register()` läuft im Kern **vor** den Migrationen – der
  Zugriff auf die Datenbank dort ließ das Modul nicht laden; (2) die Kostengrenze zählte die letzte Runde des Chats davor
  mit (Abbruch nach 0 Tokens); (3) keine Rückmeldung im Chat, wenn eine Grenze greift.
- **Echt gemessen:** Anlegen+Einrichten 39 s, 4 Züge → je genau 1 Version, kaputte Seite repariert (`tsc` ohne Fehler),
  nach 3 Versuchen genau 1 Hinweis „Ich komme nicht weiter“, Zeitgrenze meldet sich im Chat.
- **Kostengrenze echt gemessen (5.11., Codex gpt-5.6-luna):** Grenze 4 000 → 1 Aufruf, 2 836 Tokens, `limited=True`; Grenze
  100 000 → 5 Aufrufe, 24 183 Tokens, `done=True`, Seite repariert. `guard.py` (Platzgrenze) gehört zu Baustein 7.
- **Abhängigkeit:** hängende Modellaufrufe auf hydratest (Container im LAN, Ursache unbekannt) verlängerten die Läufe;
  eigener Kern-PR hydrahive/hydrahive2.0#678 (Fristen + Wiederholung). Ohne ihn sind einzelne Heilungsläufe langsamer, aber
  nicht falsch: die Zeitgrenze von 3 min fängt sie ab und meldet es im Chat.

### 7. Platz, Ruhe, Aufräumen — **umgesetzt (5.11.), echte Probe auf hydratest**
- **Gebaut:** `guard.py` (Platzgrenze 5 GB per `du -sk -- /work`, unlesbare oder fehlgeschlagene Messung gilt als „nicht ok“,
  Meldung nennt Größe und die größten Einträge, keine Pfade), `idle.py` (Leerlauf 30 min → Container stoppen, Zustand
  `sleeping`; `wake` startet, wartet auf Adresse, Zeitlimit 60 s, sonst `vibe_container_down`; Heilung weckt vor dem Lauf),
  `projects.remove` räumt zusätzlich Sitzungen ab und hält einen laufenden Zug an, `jobs.find_orphans` meldet Waisen
  (löscht nie). Dazu: Einrichtung wiederholt Netz-Schritte bis zu 3× und hält die letzten Zeilen der Fehlerausgabe fest
  (Migration `003_error_detail.sql`).
- **Echt gemessen (hydratest, ohne Modell):** Platz 144 MB → mit 5,2 GB gefüllt `ok=False` mit Meldung → aufgeräumt `ok=True`;
  40 min Leerlauf → Container aus, `sleeping`; Wecken **1,8 s**, Dev-Server danach HTTP 200 nach 1,9 s; Löschen ohne Waisen.
  Netz-Aussetzer künstlich eingebaut: 2 Aussetzer → `ready` (78 s), 3 Aussetzer → `failed` mit Schritt und Detail, „Nochmal
  versuchen“ → `ready` in 6 s.
- **Die Probe hat einen Fehler gefunden:** `npm ci` scheiterte beim Anlegen einmal ohne jede Spur (derselbe Befehl lief direkt
  danach in 2 s). **Ursache gefunden (5.11.):** `npm ci` lässt ohne Cache in 6 von 25 Läufen das native Paket
  `@rolldown/binding-linux-x64-gnu` aus (npm/cli#4828), teils mit rc=0; der Dev-Server stirbt dann mit „Cannot find native
  binding“. Behoben: Schritt `deps` prüft, ob Vite lädt, räumt `node_modules` und wiederholt (höchstens 3×): 30 von 30 ok.
- **Nicht gemessen / bewusst offen:** Die Platzgrenze ist **kein lückenloser Schutz** (ein Lauf kann innerhalb einer Runde
  füllen; echter Schutz wäre ein Pool-Typ mit Quota). Startzeit eines Containers nach langem Schlaf unter Last;
  der Leerlauf wurde durch Zurückstellen der Zeit geprüft, nicht durch 30 echte Minuten.

### 8. Vorschau und Durchreiche
- **Zuerst messen, dann bauen** (im echten Browser auf hydratest, Playwright): Reicht ein Cookie im iframe
  (`SameSite=None; Secure; Partitioned`) oder braucht es Ticket-im-Pfad? Lässt sich das iframe mit
  `frame-ancestors` einbetten? Funktioniert HMR (WebSocket) durch nginx `auth_request`? Ergebnis in diesen Plan
  eintragen („Gemessen“), erst dann Code.
- Rot (danach): Ohne gültige Anmeldung 401; Ticket gilt einmal und 60 s; Ticket eines Nicht-Admins/entfernten Admins
  ungültig; Antwort trägt `frame-ancestors <HydraHive>`, **kein** `X-Frame-Options`, **kein** `Set-Cookie` der Vorschau-
  Anwendung nach außen; fremder `Host`-Kopf in der Ticket-URL wird abgelehnt (`_HOST`-Regel); `nginx -t` schlägt fehl →
  alte Konfiguration bleibt.
- `preview_auth.py`, `preview_site.py`, `routes_preview.py`, `frontend/PreviewFrame.tsx`
  (`<iframe sandbox="allow-scripts allow-forms">`, **ohne** `allow-same-origin`).

### 9. Oberfläche
- Rot (vitest): Projektliste, „Neues Projekt“ (Name 1–60 Zeichen), Fortschritt der Einrichtung, Chat links, Vorschau rechts,
  Zeitleiste mit Klartext und „Zurück zu hier“ / „Nur diese Änderung zurück“ (jeweils mit Bestätigung), Schalter „Fehler
  selbst beheben“, `VIBE.md` ansehen/bearbeiten, klare Meldung ohne incus, Fehlerzustände mit Erklärung. Tastatur,
  Kontrast und Dialoge nach UI-Standard des Kerns (Task „UI-Standard“).
- Frontend. tsc, eslint, vitest laufen im **Kern-Worktree** (die Modul-CI lintet kein Frontend).

### 10. Abnahme auf hydratest (echt)
1. Frisches Anlegen: Projekt „Test“, Zeit bis zur ersten Vorschau messen.
2. Chat: „Mach den Hintergrund dunkelblau“ → Vorschau lädt neu, Version erscheint mit Klartext.
3. Absichtlich Fehler: „Baue einen Fehler ein“ → Agent behebt ihn selbst; unlösbarer Fehler endet nach genau 3 Versuchen.
4. „Zurück zu hier“ und „Nur diese Änderung zurück“, auch mit Konflikt.
5. Leerlauf: nach 30 min Container aus, Öffnen weckt ihn, Vorschau kommt wieder.
6. Netz: Container erreicht weder Server noch Heimnetz.
7. Mutanten-Gegenprobe der Sicherheitsregeln (ACL, `frame-ancestors`, Ticket einmalig, Fremdprojekt, Platzgrenze).
8. Aufräumen: Projekt löschen, nichts bleibt zurück (`incus list`, `network list`, nginx-Datei, Datenzeilen).

## Nicht gemessen / offen (bewusst nicht geraten)

- **ACL-Abschottung für Vibe** (Baustein 2, vor dem PR).
- **Vorschau-Anmeldung** Cookie vs. Ticket-im-Pfad, Einbetten, HMR durch nginx (Baustein 8, vor dem Code).
- **Kostengrenze je Heilungslauf** (erster Wert 100 000 Tokens, Vorschlag).
- **Browser-Fehler** über `postMessage`: ob die Nachricht aus dem sandboxed iframe zuverlässig ankommt, wird in
  Baustein 8 mit gemessen.
- **Ob ein Modul den Event-Bus des Kerns offiziell nutzen darf** (Rückfall: Abfrage).
- **Platzgrenze:** `dir`-Pool setzt keine Grenze durch. Schutz nur durch das Modul, nicht lückenlos.
- Ubuntu **26.04** im Container (Server dort, Node-Version, Image): nicht geprüft; V1 nimmt wie das Labor die
  Server-Version und holt Node selbst.

## Nicht in V1

Vorlagen außer Vite-React (V2), Veröffentlichen/ZIP/statische Seite (V2), Teilen (V3), Expertenmodus, Terminal,
Datenbanken außerhalb des Containers, Mac (kein incus), Freigabe für Nicht-Admins.

## Akzeptanzkriterien

- Alle Bausteine grün, Mutanten erkannt, CI grün, Manifest-Version angehoben.
- Abnahme 1–8 auf hydratest bestanden, Messwerte im PR.
- Kein Aufruf von `192.168.178.1`/`.3` in Tests oder Messungen.
- Nach „Projekt löschen“ bleibt nichts im Container-, Netz- oder nginx-Bestand zurück, ein zweites Vibe-Projekt und
  ein normales Projekt bleiben unverändert.
