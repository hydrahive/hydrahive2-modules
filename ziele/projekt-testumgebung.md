# Zieldokument: Projekt-Agent baut eine Testinstallation, die der Nutzer im Browser ausprobiert

> **Status:** FREIGEGEBEN (Till, 23.11.2026: „ok sehr gut, so machen wir das“)
> **Repo:** hydrahive2 (Kern); Hilfe-Artikel im Kern
> **Auslöser:** Till, 23.11.2026: Bei einem Nutzer (Windows/WSL) soll ein Projekt-Agent eine Testinstallation des
> Projekts (eine Webseite) bauen, die der Nutzer testen kann. Das geht nicht. „Es sollte auch bei Linux gehen, nicht
> nur für ihn.“
> **Verwandt:** `docs/specs/projekt-container-ausfuehrung.md` (Container-Modus), `docs/specs/container-nat-ports.md`
> (Portfreigaben), `ziele/agenten-sofortschutz.md` + `ziele/agenten-projekt-isolation*.md` (Sperren, Sandbox),
> Modul Vibe (Vorschau über Durchreiche `:8444` mit Einmal-Ticket)

## 1. Ist-Stand (am Code belegt, Stand main 666c1a98)
- **Shell-Sperre** (`core/src/hydrahive/tools/_shell_guard.py`, seit 20.11.): Für Projekt-Agenten und Spezialisten
  gesperrt sind `incus/lxc exec|shell`, `docker/podman run|exec`, `sudo`; seit 22.11. (`_shell_guard_downloads.py`)
  auch `apt-get install`, `pip install` außerhalb eines venv u. a. Erlaubt bleiben z. B. `npm ci`, `npm install`,
  `python3 -m venv`, `.venv/bin/pip install`, `uv sync`, `composer install`, `npm run dev &`,
  `python3 -m http.server`, `incus launch/start/delete`. (Geprüft mit `check_text` am deployten Code.)
- **Grund der Container-Sperre:** Der Dienst-Benutzer ist in `incus-admin`. Wer `incus exec` darf, kann einen
  privilegierten Container bauen und ist damit praktisch root auf dem Server.
- **Container-Modus gibt es** (`projects/execution.py`, `tools/_launcher_container.py`): Alle Befehle und Datei-
  zugriffe eines Projekts laufen im Projekt-Container, ohne `incus exec` in der Shell. **Aber:**
  - keine Oberfläche und keine API-Route dafür – nur die Kern-Funktion `execution.set_container()`, genutzt von
    den Modulen Vibe und Hydra-Labor;
  - die Shell-Sperre läuft in `tools/shell.py` **vor** der Wahl des Ausführungsorts – auch im Container ist
    `apt-get install` gesperrt, obwohl es dort niemandem schadet.
- **Portfreigaben** für NAT-Container gibt es (`api/routes/containers_ports.py`, Reichweite public/tailnet/off).
- **WSL:** Das Cockpit nennt Container unter WSL „meist nicht verfügbar (kein KVM/systemd-Netz)“
  (`system.json` `hint_wsl`). Ob incus auf einer aktuellen WSL läuft, ist **nicht belegt**. Laut Microsoft
  („Accessing network applications with WSL“) erreicht ein Browser unter Windows einen Server in WSL über
  `localhost`, im NAT-Modus wie im Mirrored-Modus.
- **Vibe** löst „Vorschau einer Agenten-Webseite im Browser“ schon: Container je Projekt, nginx-Durchreiche `:8444`,
  Anmeldung per Einmal-Ticket (60 s) → Cookie nur für die Durchreiche. Zugeschnitten auf neue Vite-Apps, nur Admins.
- Was beim Nutzer genau scheiterte, ist **nicht bekannt** (Meldung liegt nicht vor). Wahrscheinlich: `incus exec`,
  `docker run` oder `apt-get install` abgelehnt.

## 2. Zielbild
Ein Nutzer sagt seinem Projekt-Agenten: „Bau mir eine Testinstallation, die ich ausprobieren kann.“ Der Agent baut
sie, startet sie, und im Projekt erscheint ein Knopf **„Testseite öffnen“**. Ein Klick öffnet die Webseite im
Browser – auf Linux, unter WSL und auf dem Mac, ohne dass jemand eine Konsole öffnet. Die Sicherheitsregeln vom
20.11./22.11. bleiben für den Server unverändert in Kraft.

## 3. Zwei Wege, automatisch gewählt
**Weg A – Testumgebung im Projekt-Container** (wenn incus nutzbar ist):
1. In den Projekt-Einstellungen gibt es **„Testumgebung im Container“** (nur Projekt-Admins bzw. Admins, wie heute
   bei Projekt-Rechten). Ein Klick legt einen **unprivilegierten** Container an (`security.privileged=false`,
   `security.nesting=false`, Grenzen für CPU/RAM/Platte wie bei Vibe) und setzt den Container-Modus über die
   vorhandene Kern-Funktion. Kein neuer Weg an `execution.set_container()` vorbei.
2. Im Container gelten nur die Sperren, die den **Server** schützen: fremde Rechner, Geheimnis-Pfade, Container-
   Befehle. Installieren (`apt-get`, `pip`, `npm -g`) ist **im Container erlaubt**. Umsetzung: die Sperre bekommt
   den Ausführungsort mitgeteilt; ohne gesicherten Container-Modus gilt alles wie heute (fail-closed).
3. Ein Webserver im Container wird über eine Durchreiche erreichbar (siehe §4).

**Weg B – Testseite aus dem Workspace** (wenn incus fehlt, z. B. WSL ohne incus, Mac ohne Colima):
1. Der Agent startet den Webserver im Projekt-Workspace mit erlaubten Mitteln (`npm run dev`, venv, `uv`,
   `php -S`, `python3 -m http.server`) auf einem Port, den HydraHive dem Projekt zuteilt (Umgebungsvariable
   `HH_PREVIEW_PORT`, fester Bereich, je Projekt eindeutig).
2. Nichts wird systemweit installiert. Braucht die Seite Systempakete, meldet der Agent das als Blocker
   („Für diese Testinstallation fehlt X – ein Admin kann die Testumgebung im Container einschalten“).
3. Die Durchreiche aus §4 zeigt auf `127.0.0.1:<HH_PREVIEW_PORT>`.

Die Oberfläche zeigt, welcher Weg auf diesem Server geht, und graut Weg A aus, wenn incus fehlt – mit Erklärung.

## 4. Testseite öffnen (für beide Wege gleich)
- Knopf **„Testseite öffnen“** im Projekt, sobald unter dem zugeteilten Ziel etwas antwortet; sonst
  „Noch keine Testseite gestartet“.
- **Durchreiche** nach dem Muster von Vibe: nginx leitet nur weiter, wenn ein Cookie für genau dieses Projekt
  vorliegt; das Cookie kommt aus einem Einmal-Ticket, das nur Projekt-Mitglieder bekommen. Das Cookie öffnet keine
  HydraHive-API.
- Erreichbar über dieselbe Adresse wie HydraHive (Windows: `https://localhost:<port>`; im Netz/Tailnet über die
  Server-Adresse). Kein Öffnen ins Internet ohne ausdrückliche Admin-Freigabe (wie `scope=public` heute).
- Port und Zuteilung allgemein, keine festen Pfade dieses Servers; Installer und `update.sh` richten die nginx-
  Durchreiche auf jeder Linux-Installation ohne Handarbeit ein.

## 5. Regeln
- Allgemeingültig: Linux (Ubuntu 26.04 als Referenz), WSL, Mac – nichts nur für Tills Server oder den einen Nutzer.
- Sicherheit: kein `incus exec` in der Shell des Agenten, keine privilegierten Container, Sperren für den Server
  unverändert. Ausnahmen nur für den gesicherten Container-Modus (§3 A2), mit Tests für beide Richtungen.
- Ohne KI und ohne Container muss das Projekt weiter funktionieren wie heute.
- Deutsche Texte, Meldungen sagen, was der Nutzer jetzt tun kann.
- Hilfe-Artikel (Kern) beschreibt beide Wege und den Knopf.

## 6. Nicht-Ziele
- Kein Docker-in-Container, keine verschachtelten Container.
- Keine automatische Veröffentlichung im Internet.
- Kein Ersatz für Vibe; Vibe darf später auf dieselbe Durchreiche umziehen, muss aber nicht.

## 7. Etappen
- **E0 Messung (vor dem Bau):** Auf einer echten WSL (Tester) prüfen, ob incus installierbar ist und ein Container
  eine IPv4 bekommt; auf Ubuntu 26.04 dasselbe (Vibe-Befund 5.11.: Image `ubuntu/26.04` bekam unter incus 6.0.0 keine
  IPv4, `24.04` schon). Ergebnis entscheidet, ob Weg A unter WSL angeboten wird.
- **E1** Port-Zuteilung + Durchreiche + Knopf (Weg B zuerst, weil überall möglich).
- **E2** Container-Testumgebung per Klick (Weg A), Sperre kennt den Ausführungsort.
- **E3** Hilfe-Artikel, Live-Test auf Linux und WSL.

## 8. Abnahme-Punkte
| # | Prüfung |
|---|---|
| T1 | Messung E0 dokumentiert (WSL + Ubuntu 26.04): incus ja/nein, Container-IPv4 ja/nein, mit Befehlen und Ausgabe |
| T2 | Weg B: Projekt-Agent (echter Lauf, ohne incus) startet eine Testseite auf `HH_PREVIEW_PORT`, Knopf erscheint, Seite öffnet sich im Browser; Linux UND WSL |
| T3 | Durchreiche: ohne Ticket/Cookie 401/403; Cookie von Projekt X öffnet Projekt Y nicht; Cookie öffnet keine HydraHive-API (Tests + Live-Probe) |
| T4 | Weg A: Klick legt unprivilegierten Container an (`security.privileged=false`, `security.nesting=false` am echten Container belegt) und setzt den Container-Modus; Agent installiert im Container mit `apt-get`, Testseite öffnet sich |
| T5 | Sperre: im Container-Modus `apt-get install` erlaubt; `ssh`, Geheimnis-Pfade, `incus exec` weiter gesperrt; im Host-Modus alles wie heute (Tests beide Richtungen, Gegenprobe rot) |
| T6 | Fehlt incus: Weg A ausgegraut mit Erklärung, Weg B funktioniert; kein Fehler, kein Rückfall auf den Server |
| T7 | Installer + `update.sh` richten die Durchreiche ohne Handarbeit ein (frische 26.04-Installation im Container geprüft) |
| T8 | Hilfe-Artikel (de) beschreibt beide Wege und den Knopf, gegen Code geprüft |
