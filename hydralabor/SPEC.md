# Hydra-Labor – sicher an HydraHive mitbauen

> Neues Modul `hydralabor`. Idee von Till (30.10.2026), Task 2dbf77c4.
> **Status: Plan, Fragen von Till beantwortet (30.10.). Gebaut wird erst nach Tills Freigabe, Etappe für Etappe.**
> Name: „Hydra-Labor“ (Till 30.10.). „Werkstatt“ ist im Kern schon ein Bereich (`/werkstatt`).

## Problem

Externe Nutzer betreiben ein **eigenes HydraHive auf eigenem Server**. Wir haben darauf keinen Zugriff. Einige bauen
selbst an HydraHive herum: Sie richten sich einen Dev-Agenten mit Shell ein, der direkt auf ihrem Server arbeitet.
Dabei machen sie ihr System kaputt (falsche Pakete, gelöschte Dateien, verbogene Konfiguration). Ihre Verbesserungen
kommen außerdem nie bei uns an.

Heute läuft jeder Befehl eines Agenten **auf dem Server** (`tools/_launcher.py`, nur `DevLauncher`). Eine Stelle für
eine andere Ausführung ist vorgesehen („Implementations decide on isolation level“), aber nicht gebaut.

## Ziel

1. **Nichts kaputt machen können:** Der Agent im Labor arbeitet nur in einem eigenen Container. Der Server bleibt
   unberührt, auch wenn der Agent oder der Nutzer Unsinn macht.
2. **Ohne Vorwissen einrichten:** Ein Einrichtungs-Assistent führt Schritt für Schritt durch, mit Knöpfen, ohne
   Terminal, ohne Git-Kenntnisse.
3. **Beitragen ohne Git:** „Änderung einreichen“ und „Fehler melden“ per Knopf. Daraus werden ein PR bzw. ein Issue
   bei `hydrahive/hydrahive2.0` (Kern), `hydrahive/hydrahive2-modules` (Module) oder optional
   `hydrahive/hydrahive2-plugins` (Plugins). Till prüft und übernimmt.
4. **Zurück auf Anfang:** Ein Knopf setzt den Container auf den letzten guten Stand zurück.

## Rahmen (Entscheidungen Till, 30.10.)

- Nutzer haben **eigene Server**, wir haben keinen Zugang. Es gibt also keinen gemeinsamen Bot-Zugang: Jeder Schlüssel
  im Modul läge beim Nutzer offen.
- Einreichungen landen **direkt auf GitHub** (nicht auf Tills Gitea).
- „Commits ohne PR“ heißt: Der Nutzer stellt Änderungen bereit, **Till prüft und übernimmt**. Technisch ist das ein PR,
  den aber das Modul anlegt.

## Aufbau

```
 Server des Nutzers (eigenes HydraHive)
 ┌──────────────────────────────────────────────────────────────────────┐
 │ Modul „Hydra-Labor“                                                   │
 │  • Einrichtungs-Assistent                                             │
 │  • Labor-Agent (fest eingerichtet)                                    │
 │  • GitHub-Verbindung des Nutzers (Token verschlüsselt, nur hier)      │
 │  • „Änderung einreichen“ / „Fehler melden“ / „Zurücksetzen“          │
 │                │ jeder Befehl des Labor-Agenten                       │
 │                ▼                                                      │
 │  Container „hh-labor-<projekt>“ (incus, eigenes Netz)                 │
 │   • Klon des Repos (Fork des Nutzers), Testumgebung                   │
 │   • KEIN GitHub-Token, kein Zugriff auf den Server                    │
 └──────────────────────────────────────────────────────────────────────┘
                 │ Modul (nicht der Container) schiebt den Branch, legt PR/Issue an
                 ▼
 GitHub: Fork des Nutzers ──PR──▶ hydrahive/hydrahive2.0 bzw. hydrahive2-modules ◀── Till prüft
```

## Teil 1 (Kern): Befehle eines Projekts laufen im Container

Damit das Labor sicher ist, braucht der Kern eine neue Fähigkeit. Sie hilft auch allgemein: Task 3bd963b2 c)
„Shell pro Nutzer isolieren“.

- **Projekt-Einstellung „Ausführung“:** `host` (wie heute) oder `container:<name>`. Nur Admins dürfen sie setzen.
  Module setzen sie über eine Kern-Funktion, nicht über die Datenbank.
- **Neuer Launcher `ContainerLauncher`:** `shell_exec` führt aus mit
  `incus exec <ct> --cwd /work --user 1000 --env … -- bash -lc '<befehl>'`.
  - Der Befehl geht als ein Argument hinein, ohne Einbau in eine Host-Shell. Der Host-Teil des Befehls ist fest.
  - Zeitlimit und Abbruch wie heute. Bei einem Abbruch wird die Prozessgruppe **im Container** beendet.
  - **Keine** Kern-Umgebungsvariablen (GH_TOKEN, GITEA_TOKEN, Pfade des Servers) im Container.
- **Datei-Werkzeuge** (`file_read`, `file_write`, `file_patch`) arbeiten bei einem Container-Projekt im Container.
  Weg: `incus file pull/push` auf `/work/…`, mit derselben Pfadprüfung wie `safe_path`, nur bezogen auf `/work`.
- **Gesperrt** bei einem Container-Projekt: Werkzeuge, die auf den Server greifen (Browser mit lokalen Dateien,
  Plugins ohne Workspace-Grenze, `webmin_*`, Mount-Werkzeuge). Die Liste steht im Kern, nicht im Modul.
- **Ohne incus** (z. B. Mac ohne Colima): Container-Projekte gehen nicht. Das Labor zeigt das klar an.

**Tests:** Ein Befehl landet nur im Container (Attrappe für incus, kein Host-Prozess). Pfade außerhalb von `/work`
werden abgelehnt. Keine Token in der Umgebung. Ein Abbruch beendet nur den Container-Prozess. Gesperrte Werkzeuge
sind nicht verfügbar. Ein Projekt ohne die Einstellung verhält sich wie heute (Gegenprobe).

## Teil 2 (Modul): Hydra-Labor

### Einrichtungs-Assistent (Seite „Labor einrichten“)

Jeder Schritt hat einen Knopf und zeigt grün/rot mit Erklärung in einfachen Worten.

1. **Voraussetzungen prüfen** (nur lesen): incus da? Netz für Container? genug Platz (mind. 15 GB) und RAM
   (mind. 4 GB frei)? Fehlt etwas, erklärt der Assistent, was zu tun ist, z. B. „Container-Manager in den Einstellungen
   einschalten“.
2. **Mit GitHub verbinden**: Knopf „Mit GitHub verbinden“.
   - Weg: GitHub-**Device-Flow** über eine eigene OAuth-App von HydraHive. Das Modul zeigt einen Code und den Link
     `github.com/login/device`. Der Nutzer gibt dort den Code ein und bestätigt. Er tippt kein Passwort und keinen
     Token ein.
   - Gefragte Rechte: `public_repo` (Fork, Branch, PR, Issue in öffentlichen Repos). Nichts weiter.
   - Der Token liegt **verschlüsselt im Modul** (Master-Schlüssel des Kerns), nie im Container, nie in Logs.
   - Ohne GitHub-Konto: Link „Konto anlegen“, danach weiter.
3. **Labor anlegen**: Knopf „Labor anlegen“. Das Modul macht:
   - einen Fork von `hydrahive/hydrahive2.0` und `hydrahive2-modules` beim Nutzer, falls noch keiner da ist;
     `hydrahive2-plugins` nur, wenn der Nutzer das Häkchen „Auch an Plugins mitarbeiten“ setzt (Standard aus);
   - ein Projekt „Hydra-Labor“ mit Ausführung im Container;
   - den Container (Ubuntu wie der Server, Grenzen Standard 2 CPU / 4 GB RAM / 20 GB, Netz NAT, kein Zugang zum Heimnetz);
   - im Container: Klon des Forks (ohne Zugangsdaten), Python-Umgebung, Node, Testabhängigkeiten. Fortschritt mit
     Balken. Dauer grob 5–15 min (vorher messen);
   - einen **Schnappschuss „frisch“** zum Zurücksetzen.
4. **Labor-Agent**: wird fest angelegt (siehe unten). Knopf „Zum Labor-Chat“.
5. **Fertig**: kurze Einführung „So arbeitest du im Labor“ mit drei Beispielen („Finde den Fehler …“, „Baue mir …“,
   „Reiche meine Änderung ein“).

Der Assistent kann jederzeit fortgesetzt werden. Bricht ein Schritt ab, zeigt er den Grund und „Nochmal“.

### Labor-Agent (fest eingerichtet)

- Systemprompt mit den HydraHive-Regeln (Spec zuerst, rote Tests, ≤ 200 Zeilen je Datei, keine Secrets, Texte de/en)
  und dem Satz „Du arbeitest nur im Labor-Container. Den Server kannst und darfst du nicht verändern.“
- Werkzeuge: `shell_exec`, `file_*` (laufen im Container), `todo_write`, `load_skill`, Websuche. **Kein** `ask_agent`
  nach außen, keine Mail, kein Discord, keine Medien-Werkzeuge mit Kosten.
- Skills: `test`, `debugging`, `code-review`, eine Labor-Kurzfassung von `hh-review`.
- Modell: wählt der Nutzer im Assistenten aus seinen vorhandenen Anbietern. Das Labor bringt keinen eigenen Schlüssel mit.
- **Nicht umstellbar** über die normale Agenten-Seite: Werkzeuge und Ausführung sind gesperrt. Die Prüfung macht der
  Kern, der Agent ist als „verwaltet von Modul hydralabor“ markiert. Nur das Modell darf der Nutzer ändern.

### Arbeiten im Labor (Seite „Labor“)

- Stand des Containers (läuft / aus), belegter Platz, aktueller Branch, geänderte Dateien.
- **„Testlauf“**: startet die Tests im Container und zeigt das Ergebnis.
- **Probe-Installation** (Till 30.10.: gewünscht): Knopf „Probe-HydraHive starten“.
  - Im Container läuft ein vollständiges HydraHive aus dem Labor-Stand (Backend + gebaute Oberfläche), mit eigenen
    leeren Daten und eigenem Test-Admin. Es hat keinen Zugriff auf die Daten des echten Systems.
  - Erreichbar nur über das Modul: Link „Probe öffnen“, der Kern leitet mit Anmeldung des Admins durch (kein offener
    Port nach außen).
  - Knöpfe „Probe neu bauen“ (nach Änderungen) und „Probe stoppen“. Bauzeit und Speicher vorher messen.
  - Module aus dem Labor lassen sich in der Probe installieren, um sie auszuprobieren.
- **„Zurücksetzen“** mit eigenem Dialog: auf „frisch“ oder auf einen eigenen Schnappschuss („Stand merken“).

### Änderung einreichen

Knopf „Änderung einreichen“ → Dialog: Titel, „Was ändert sich und warum?“ (2–3 Sätze), Ziel (Kern, Module oder –
wenn eingerichtet – Plugins). Das Ziel ergibt sich meist aus den geänderten Dateien; der Dialog schlägt es vor.
Das Modul macht dann:

1. **Vorprüfung im Container**, alles muss grün sein:
   - Tests laufen grün (die passende Reihe zum geänderten Bereich).
   - Keine geschützten Pfade geändert (`.github/`, `installer/`-Kernteile, `scripts/check_*`, Lizenz).
     Die Liste steht im Modul, mit Begründung.
   - Kein Geheimnis im Diff (Muster wie im Kern: `ghp_`, `gho_`, `sk-`, private Schlüssel …).
   - Größe vernünftig (Standard ≤ 50 Dateien / ≤ 3.000 Zeilen, sonst Hinweis „bitte aufteilen“).
   - Bei Modulen: Manifest-Version angehoben (`check_version_bump`).
2. **Branch** `labor/<kurzname>-<datum>` im Fork. Der Commit entsteht im Container, das **Schieben macht das Modul**
   mit dem Token, über ein einmaliges Bündel (`git bundle`). Der Container sieht den Token nie.
3. **PR** an das Haupt-Repo, Text: Beschreibung des Nutzers, Prüfergebnis, Hinweis „eingereicht über Hydra-Labor“.
   Absender ist das eigene GitHub-Konto des Nutzers.
4. Das Modul zeigt den Stand: eingereicht → in Prüfung → übernommen / abgelehnt (mit Kommentar von GitHub).

### Fehler melden

Knopf „Fehler melden“ → Formular: Was ist passiert, was hast du erwartet, Schritte. Das Modul hängt automatisch an:
HydraHive-Version, Modul-Versionen, Betriebssystem. Logs nur nach Rückfrage und durch den Secret-Filter. Daraus wird
ein Issue mit Label `labor`.

### Rechte

- **Nur Admins** (Till 30.10.): Freigabe `module.hydralabor` fest `admin_only`. Das Labor belegt Rechner und Platz
  und arbeitet mit einem GitHub-Konto.
- Ein Labor je Server.

## Etappen

1. **K1 (Kern):** Projekt-Ausführung im Container (Launcher + Datei-Werkzeuge + Sperrliste), verwaltete Agenten.
2. **L1 (Modul):** Assistent Schritte 1, 3, 4, 5 (ohne GitHub), Labor-Seite, Testlauf, Zurücksetzen.
   Damit ist das System schon sicher, auch ohne Einreichen.
3. **L2 (Modul):** GitHub-Verbindung (Device-Flow), Fork, „Änderung einreichen“, „Fehler melden“, Status.
4. **L3 (Modul):** Probe-Installation im Container, Schnappschüsse verwalten, Plugins als drittes Ziel,
   Anleitung im Hilfe-Bereich (de/en).

## Was Till vorher einrichten muss

- **GitHub-OAuth-App „HydraHive Labor“** in der Organisation `hydrahive`, mit Device-Flow an. Die Client-ID ist
  öffentlich und darf im Modul stehen (beim Device-Flow gibt es kein Client-Secret).
- Label `labor` in den Repos (Kern, Module, Plugins). Optional eine Vorlage für PRs aus dem Labor.

## Prüfung

- Rote Tests zuerst, Mutanten, Gegenprobe gegen `main`.
- **Ausbruchs-Proben** (wichtigster Teil): Der Labor-Agent versucht gezielt, den Server zu erreichen – Datei
  außerhalb von `/work` schreiben, `incus` im Container, Server-IP und Ports, Token in der Umgebung, Kern-Werkzeuge
  aufrufen. Alles muss scheitern.
- Echte Probe auf hydratest: Assistent komplett durchklicken, mit einem Test-GitHub-Konto einen PR an ein
  **Test-Repo** stellen (nicht an das echte), zurücksetzen, E2E in 4 Breiten.

## Entscheidungen (Till, 30.10.)

1. Name „Hydra-Labor“: ja.
2. Nur Admins legen ein Labor an.
3. Probe-Installation im Container: ja (Etappe L3).
4. Ziele: Kern und Module; Plugins optional, wenn eingerichtet.

## Nicht in diesem Plan

- Mitarbeit an Tills Gitea.
- Zugriff von uns auf die Server der Nutzer.
- Automatisches Übernehmen von PRs.
