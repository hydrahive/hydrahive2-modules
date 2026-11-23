# Zieldokument A: Sofortschutz – Agenten laden und installieren nichts

> **Status:** FREIGEGEBEN (Till, 23.11.2026: „ja ich gebe beides frei“)
> **Repo:** hydrahive2 (Kern), `core/src/hydrahive/tools/_shell_guard.py`
> **Auslöser:** 22.11.2026: Projekt-Agent lädt ungefragt PowerShell (538 MB) per `curl` nach /tmp, entpackt und startet
> es (Auftrag b4b1f5ee). Till 23.11.: „das ist mir zu gefährlich … wenn ein Lauf fertig ist, kann es schon zu spät sein.“
> **Rolle:** Überbrückung, bis Zieldokument B (eigener Benutzer je Projekt) umgesetzt ist. Eine Wortliste ist keine Mauer.

## 1. Regeln (gelten für Agent-Typ `project` und `specialist`, nicht für Buddy/Master)
Ablehnung ohne Rückfrage, mit klarem Hinweis an den Agenten („Herunterladen/Installieren ist für Projekt-Agenten
gesperrt. Melde es als Blocker.“):
1. **Dateien aus dem Netz speichern:** `curl` mit `-o/-O/--output/--remote-name` oder Umleitung `>`/`>>`/`| tee`;
   `wget` (außer `--spider`/`-O -`); `aria2c`, `axel`.
2. **Aus dem Netz direkt ausführen:** `curl …|sh`, `wget …|bash`, `| python`, `bash <(curl …)`, `source <(…)`.
3. **Pakete systemweit oder global installieren:** `apt`, `apt-get`, `dpkg -i`, `snap install`, `flatpak install`,
   `pip install` außerhalb eines virtuellen Umfelds im Arbeitsordner (`--user`, `--break-system-packages`, ohne aktive
   venv), `pipx install`, `npm i -g`/`npm install --global`, `yarn global add`, `pnpm add -g`, `gem install`,
   `cargo install`, `go install`, `brew install`.
4. **Fremde Programme aus /tmp, /var/tmp oder dem Home starten**, die nicht aus dem Repo stammen (Muster: `chmod +x`
   auf eine Datei außerhalb des Arbeitsordners, Ausführen von `/tmp/...`).

## 2. Erlaubt bleibt
- Webseiten lesen: `curl`/`wget -O -` ohne Datei, Ausgabe nur auf den Bildschirm.
- `git clone/fetch/pull/push`, `gh`.
- Abhängigkeiten **im eigenen Arbeitsordner** nach Lockfile: `npm ci`, `pnpm install --frozen-lockfile`,
  `pip install` in einer `.venv` im Arbeitsordner, `uv sync`.
- Alles, was Tests und Linter des Repos schon mitbringen.

## 3. Begleitend
- `ask_agent`: Jeder Auftrag an Projekt-Agenten/Spezialisten bekommt automatisch den Satz „Nichts herunterladen oder
  installieren; was fehlt, als Blocker melden.“ (im Kern, nicht im Prompt des Buddys).
- Jede Ablehnung wird im Fehlerprotokoll festgehalten (Agent, Befehl geschwärzt, Zeit), damit Till Versuche sieht.

## 4. Abnahme
| # | Prüfung |
|---|---|
| S1 | Tests je Regel 1–4 mit echten Befehlen (inkl. des PowerShell-Befehls vom 22.11.) → abgelehnt; Gegenprobe ohne Fix rot |
| S2 | Tests §2 → erlaubt (curl auf stdout, git, gh, npm ci, pip in .venv) – kein Fehlalarm wie beim `grep 'ssh'` am 22.11. |
| S3 | Buddy/Master nicht betroffen (Test) |
| S4 | Ablehnungen stehen im Fehlerprotokoll, ohne Geheimnisse |
| S5 | Live nach Deploy: Projekt-Agent versucht `curl -o /tmp/x https://example.com` → abgelehnt, Eintrag sichtbar |
