# Zieldokument B: Eigener Linux-Benutzer je Projekt – Agenten sehen nur ihr Projekt

> **Status:** FREIGEGEBEN (Till, 23.11.2026: „ja ich gebe beides frei“)
> **Repo:** hydrahive2 (Kern + Installer), Module, wo sie Projektdateien schreiben
> **Auslöser:** 20.11.2026 (Spezialist per ssh auf Tills Workstation, sudo, Mirror-Datenbank und HH_SECRET_KEY gelesen),
> 22.11.2026 (PowerShell-Download). Till 23.11.: „pro Projekt ein eigener User, mit Projektusern und Gruppen arbeiten;
> alles, was zum Projekt gehört, in den Projekt-Workspace; Configs und Secrets außerhalb. Der einzige, der noch Vorrang
> haben sollte, ist Buddy – der kann den Projektumschalter nutzen.“

## 1. Ist-Stand (gemessen am 23.11.2026)
- Der Dienst und **alle** Agenten-Befehle laufen als ein Benutzer `hydrahive` (uid 1001). Er ist Mitglied von `sudo`,
  `disk`, `kvm`, `incus-admin`. sudo verlangt hier ein Passwort; auf der Workstation war es am 20.11. passwortlos.
- `hydrahive` darf alles lesen, was HydraHive hat: `/etc/hydrahive2` (Zugangsdaten, Schlüssel, `pg_mirror.dsn`,
  `users.json`), alle Projekt-Workspaces, alle Datenbanken.
- Die heutige Sperre (`_shell_guard.py`) ist eine Wortliste. Sie selbst sagt: „Kein vollständiger Shell-Parser: wer per
  eval/base64 verschleiert, kommt durch. Die echte Mauer wäre ein eigener Unix-User ohne sudo.“
- **Im Projekt-Workspace von „Hydrahive DEV“ liegt ein privater SSH-Schlüssel** (`.ssh/id_hhmaster`) und ein Symlink
  nach außen (`_work → /srv/hh-arbeit/work/_work`).

## 2. Zielbild
1. **Je Projekt ein Linux-Benutzer und eine Gruppe** (z. B. `hhp-<kurz-id>`), ohne Login, ohne sudo, ohne Mitgliedschaft
   in `sudo`, `disk`, `kvm`, `incus-admin`, `docker`.
2. **Befehle von Projekt-Agenten und Spezialisten** dieses Projekts (shell_exec, Datei-Werkzeuge, Hintergrundprozesse)
   laufen als dieser Benutzer – durchgesetzt vom Kern, nicht vom Agenten wählbar.
3. **Der Projekt-Workspace gehört dem Projektbenutzer** (Gruppe: Projektgruppe; der Dienstbenutzer `hydrahive` ist
   Mitglied jeder Projektgruppe, damit die Oberfläche weiter lesen und schreiben kann). Projekte sehen sich gegenseitig
   nicht.
4. **Alles, was zum Projekt gehört, liegt im Workspace:** Repos, Worktrees, Arbeits- und Testordner (heute u. a.
   `/srv/hh-arbeit/work/_work`), Caches, Logs der Agenten. Keine Symlinks nach außen.
5. **Alles, worauf Agenten nie Zugriff haben dürfen, liegt außerhalb und ist für Projektbenutzer unlesbar:**
   `/etc/hydrahive2`, `/var/lib/hydrahive2` außer `workspaces/projects/<id>`, Datenbanken, Zugangsdaten, SSH-Schlüssel,
   Mirror-Zugang, Sitzungen anderer.
6. **Netz:** Projektbenutzer erreichen nur, was die Arbeit braucht (GitHub, Paketquellen für Lockfile-Installationen,
   die HydraHive-API über den Kern). Nicht: das Heimnetz (192.168.0.0/16 u. a.), andere Rechner per ssh. Umsetzung
   z. B. per nftables-Regel nach Benutzer-ID (`meta skuid`).
7. **Zugangsdaten für Agenten** (GitHub-Token u. a.) bekommt ein Lauf nur als Umgebungsvariable für genau diesen
   Befehl, nie als lesbare Datei – wie heute über die Credential-Einspeisung.
8. **Buddy (Master)** bleibt beim Dienstbenutzer und behält Vorrang. Wechselt Till im Buddy das Projekt
   (Projektumschalter), arbeitet Buddy in diesem Projekt – entscheiden: als Projektbenutzer (sicherer) oder weiter als
   Dienstbenutzer (wie heute). Empfehlung: Buddy-Befehle im Projektkontext ebenfalls als Projektbenutzer, nur
   ausdrückliche Admin-Aufgaben als Dienstbenutzer.

## 2a. Ohne Handarbeit (Till, 23.11.2026: „das kann kein normaler User, der es gerade mal schafft, HydraHive zu installieren“)
- **Kein Nutzer legt Benutzer, Gruppen oder Netzregeln von Hand an.** Alles richtet HydraHive selbst ein:
  - **Neuinstallation:** der Installer (läuft als root) legt Grundgerüst, Rechte und Netzregeln an.
  - **Bestehende Installationen:** das normale Update (`update.sh` über `hydrahive2-update.timer`, läuft als root)
    zieht dasselbe nach – idempotent, ohne Rückfrage.
  - **Neues Projekt in der Oberfläche:** Projektbenutzer/-gruppe entstehen automatisch über einen schmalen Root-Helfer
    nach dem Vorbild `hh-portforward` (eigene sudoers-Zeile nur für genau diesen Helfer; der Helfer prüft jede Eingabe
    selbst, z. B. nur Projekt-IDs im erwarteten Format, nur Benutzer mit Präfix `hhp-`). Löschen eines Projekts
    entfernt Benutzer und Gruppe wieder.
  - Alternative ohne dauerhafte Benutzerkonten (systemd `DynamicUser`, `systemd-run --property=DynamicUser=yes`,
    bubblewrap): in B0 prüfen – wenn sie dasselbe Schutzniveau ohne Helfer erreicht, ist sie vorzuziehen.
- Schlägt die Einrichtung fehl, läuft HydraHive weiter wie bisher und zeigt im Cockpit einen deutlichen Hinweis
  („Projekt-Isolation nicht aktiv“) – kein stilles Zurückfallen.

## 3. Etappen
| Etappe | Inhalt |
|---|---|
| B0 | Bestandsaufnahme: alle Stellen, die Prozesse für Agenten starten (shell, Hintergrundjobs, Module wie vibe/hydralabor/game-studio, Datei-Werkzeuge), alle Pfade, die Agenten heute außerhalb ihres Workspace nutzen, Geheimnisse innerhalb von Workspaces (z. B. `.ssh/id_hhmaster`). Ergebnis: Liste + Plan, nichts ändern. |
| B1 | Installer/Kern: Projektbenutzer und -gruppe anlegen/entfernen beim Anlegen/Löschen eines Projekts (Helfer mit eng begrenztem sudo-Recht nur dafür, oder systemd `DynamicUser`-artig – im Plan entscheiden). Rechte auf dem Workspace setzen. |
| B2 | Befehle von Projekt-Agenten/Spezialisten als Projektbenutzer starten (z. B. `systemd-run --uid … --property=…` oder ein kleiner Starter mit `setpriv`), inkl. Datei-Werkzeuge. |
| B3 | Umzug: Arbeitsordner, Worktrees, Caches in die Workspaces; Geheimnisse raus; Symlinks nach außen entfernen. |
| B4 | Netzregeln je Projektbenutzer. |
| B5 | Buddy-Projektumschalter wie in §2.8 entschieden. |
| B6 | Live-Abnahme. |

## 4. Abnahme
| # | Prüfung |
|---|---|
| P1 | Projekt-Agent kann `/etc/hydrahive2/*`, fremde Workspaces, `/var/lib/hydrahive2/*.db`, `~hydrahive/.ssh` nicht lesen (Test als Projektbenutzer: Permission denied) – auch per `python -c`, `base64`, `eval` (nicht über Wortliste, sondern durch Rechte) |
| P2 | `sudo` als Projektbenutzer unmöglich (nicht in sudoers, keine Gruppe) |
| P3 | `ssh 192.168.x.x` und Verbindungen ins Heimnetz scheitern auf Netzebene; GitHub geht |
| P4 | Normale Projektarbeit läuft: git, gh, Tests, npm ci/.venv, Modul-Container-Arbeiten, die das Projekt braucht |
| P5 | Oberfläche (Dateien, Cockpit) liest/schreibt Workspaces weiter |
| P6 | Keine Geheimnisse, keine Symlinks nach außen in Workspaces (Prüfskript in CI/Installer) |
| P8 | Neuinstallation und Update auf einer frischen VM ohne jede Handarbeit: Projekt anlegen in der Oberfläche → Projektbenutzer existiert, Agent läuft als dieser; Projekt löschen → Benutzer weg; Fehlschlag sichtbar im Cockpit |
| P7 | Live: der Angriff vom 20.11. (ssh + sudo + cat pg_mirror.dsn) und der Download vom 22.11. als Projekt-Agent nachgestellt → scheitert, auch verschleiert |
