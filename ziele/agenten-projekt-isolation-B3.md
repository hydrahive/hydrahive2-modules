# Nachtrag B3: Sandbox allgemeingültig – Allowlist statt Sperrliste, Freigaben je Projekt

Gehört zu `ziele/agenten-projekt-isolation.md` (Abnahme P1–P8 gilt weiter) und `…-B0.md`.
Freigabe Till 23.11.2026: Variante **a** („SSD behalten, gezielt freigeben“) und
**„es darf NICHTS nur auf uns gebaut sein, ALLES muss auch für andere passen“.**

## 1. Anlass (gemessen 23.11.2026)

- B2a (#755, `b72ab41d`, Schalter `HH_AGENT_SANDBOX` aus) versteckt eine **feste Liste** von Pfaden
  (`_launcher_sandbox._HIDDEN`: `/etc/hydrahive2`, `/var/lib/hydrahive2`, `/home`, `/root`, `/srv`, …).
  Das passt nur für unseren Server. Daten- und Konfig-Ordner sind einstellbar (`HH_DATA_DIR`, `HH_CONFIG_DIR`,
  `settings/_paths.py`); der Mac-Installer nutzt `/usr/local/var/hydrahive2` und `/usr/local/etc/hydrahive2`;
  System-Archiv-Platten liegen unter `<beliebiger Einhängepunkt>/hydrahive-archiv` (`installer/lib/archive-disk.sh`).
  Bei solchen Installationen wären Geheimnisse und fremde Workspaces in der Sandbox **sichtbar**.
- Hydrahive DEV arbeitet auf einer zweiten SSD (`/srv/hh-arbeit`, Task 2a02ca15): Worktrees (`_work`, 2,2 GB),
  Test-Umgebungen (`venv-test`, `venv-312`, `venv-ci`, `python`), Caches, `umgebung.sh`. Mit Sandbox an wäre das
  leer → keine Tests, keine Worktrees. Das ist ein Sonderfall **unseres** Servers, keiner für den Kern.
- In `_work/.ht_tok` liegt ein Token, das der Projekt-Agent heute lesen kann.

## 2. Zielbild

1. **Allowlist.** Die Sandbox startet leer und blendet nur ein:
   - System lesend: `/usr`, `/bin`, `/sbin`, `/lib*`, `/opt` und `/etc` (ohne den Konfig-Ordner), dazu was zum
     Laufen nötig ist (`/dev`, eigenes `/proc`, eigenes `/tmp`).
   - der eigene Workspace (schreibend), verknüpfte Projekte (lesend, wie heute),
   - die **Freigaben des Projekts** (§3).
   Alles andere fehlt – egal welche Platten, Einhängepunkte oder Datenorte eine Installation hat.
2. **Eigene Pfade aus den Einstellungen.** Daten- und Konfig-Ordner (`settings.data_dir`, `settings.config_dir`)
   und das Archiv bleiben unsichtbar, auch wenn sie unter `/opt`, `/usr/local` oder `/etc` liegen. Kein fester Pfad
   im Kern.
3. **Unterschiede der Systeme.** Wo bwrap fehlt (Mac, Container ohne User-Namespaces): Befehl wird abgelehnt mit
   verständlicher Meldung, nie ungeschützt ausgeführt (wie B2a). Im Cockpit sichtbar, ob die Sandbox auf dieser
   Installation verfügbar ist.

## 3. Freigaben je Projekt

- Neues Projektfeld `sandbox_mounts`: Liste aus `{"path": "/…", "mode": "ro"|"rw"}` (höchstens 20).
- **Setzen nur Admins** – in den Projekt-Einstellungen im Cockpit (Feld „Zusätzliche Ordner für Agenten“), API
  admin-only. Gespeichert in der Projekt-Konfig unter dem Datenordner; die ist in der Sandbox unsichtbar, Agenten
  können ihre Freigaben also weder lesen noch ändern. Kein Agenten-Werkzeug zum Setzen.
- Prüfung beim Speichern **und** beim Start jedes Befehls (realpath):
  - absoluter Pfad, existiert, ist ein Ordner;
  - nicht `/` und nicht einer der System-Ordner selbst;
  - nicht Daten-, Konfig- oder Archiv-Ordner, nicht darin und nicht darüber (sonst wären Geheimnisse sichtbar);
  - nicht der Workspace eines anderen Projekts (dafür gibt es verknüpfte Projekte).
  Ungültige Freigabe → wird nicht eingeblendet, Hinweis im Fehlerprotokoll und im Cockpit.
- Symlinks im Workspace, die auf eine Freigabe zeigen (z. B. `_work → /srv/hh-arbeit/work/_work`), funktionieren
  dann wie bisher, weil das Ziel unter gleichem Pfad eingeblendet wird.
- Für unseren Server (nur Konfiguration, nichts im Kern): Hydrahive DEV bekommt `/srv/hh-arbeit/work/_work` rw,
  `/srv/hh-arbeit/cache` rw, `/srv/hh-arbeit/venv-test`, `venv-312`, `venv-ci`, `python` ro, `umgebung.sh` liegt
  dann besser in `work/_work` oder wird per ro-Ordner freigegeben. Vorher `_work/.ht_tok` herausnehmen
  (Token gehört in den Credential-Speicher).

## 4. Prüfskript (aus B3 alt)

- Kern-Funktion + Admin-Ansicht: alle Workspaces auf private Schlüssel (`id_*`, `*.pem` mit PRIVATE KEY),
  `.env`/Token-Dateien und Symlinks nach außen prüfen; Symlinks nach außen ohne passende Freigabe melden.
- Nur melden, nichts löschen oder verschieben.

## 5. Abnahme (ergänzt P1–P8)

| # | Prüfung |
|---|---|
| B3-1 | Test mit `HH_DATA_DIR`/`HH_CONFIG_DIR` an ungewöhnlichem Ort (z. B. unter `/opt/…` und unter `/etc/…`) und einer Archiv-Platte unter einem fremden Einhängepunkt: in der Sandbox unsichtbar (echter bwrap-Lauf) |
| B3-2 | Pfade außerhalb der Allowlist (z. B. `/srv`, `/mnt`, `/media`, `/data`, `/home`) sind leer bzw. fehlen, ohne dass sie im Kern genannt werden |
| B3-3 | Freigabe rw/ro wirkt: rw schreibbar, ro nicht; Freigabe auf Daten-/Konfig-/Archiv-Ordner, `/`, System-Ordner oder fremden Workspace wird beim Speichern abgelehnt **und** beim Start nicht eingeblendet (Gegenprobe: Prüfung aus → Test rot) |
| B3-4 | Nur Admins setzen Freigaben (API-Test: Nicht-Admin 403); kein Agenten-Werkzeug ändert sie |
| B3-5 | Ohne bwrap: Ablehnung mit Meldung, Cockpit zeigt „Sandbox nicht verfügbar“ |
| B3-6 | Prüfskript findet einen eingeschmuggelten privaten Schlüssel und einen Symlink nach außen ohne Freigabe |
| B3-7 | Live auf unserem Server mit Schalter an: Projekt-Agent Hydrahive DEV fährt die volle Kern-Testreihe aus `venv-test` und arbeitet in einem `_work`-Worktree; `/etc/hydrahive2`, `/var/lib/hydrahive2` und `/srv/hh-container` sind leer |

## 6. Reihenfolge

1. B3a Allowlist + Pfade aus Einstellungen (ersetzt `_HIDDEN`), Tests B3-1/B3-2/B3-5.
2. B3b `sandbox_mounts` (Feld, Prüfung, API admin-only, Cockpit-Feld, Hilfe-Text), Tests B3-3/B3-4.
3. B3c Prüfskript, Test B3-6.
4. Unser Server: Token aus `_work` umziehen, Freigaben setzen; nach Tills Deploy Schalter an, B3-7.

Arbeitsteilung: Sandbox-Kern (B3a, B3b-Prüfung) baut der Buddy selbst (Regel seit 20.11.: Sperren gegen Agenten
baut kein Agent). Cockpit-Feld und Hilfe-Text darf der Projekt-Agent bauen, Diff wird geprüft.
