# B0 – Bestandsaufnahme Agenten-Isolation (23.11.2026, Buddy, nur gelesen/getestet, nichts geändert)

## Kernbefund: Es geht ohne Benutzer anlegen
`bubblewrap` (bwrap) ist auf **jeder** HydraHive-Installation schon da und funktioniert **ohne root**:
- Installer `modules/00-deps.sh:64` und `update.sh:137` rufen `lib/debian-document-tools.sh` → installiert
  `bubblewrap` + AppArmor-Profil `hydrahive-bwrap-userns` (nötig auf Ubuntu 24.04+/26.04 mit
  `apparmor_restrict_unprivileged_userns=1`). Läuft heute schon für den PDF-Leser (`tools/_document_process.py:68-82`).
- Live-Probe als Dienstbenutzer (ohne sudo) auf diesem Server:
  `bwrap --ro-bind / / --tmpfs /etc/hydrahive2 --tmpfs /var/lib/hydrahive2 --bind <workspace> <workspace> --unshare-pid …`
  → `/etc/hydrahive2` leer (0 Einträge), andere Projekte nicht sichtbar, Workspace schreibbar, `/opt` nicht
  schreibbar, nur 6 Prozesse sichtbar.
- `--unshare-net` trennt das Netz komplett (Probe: KEIN_NETZ). Gefiltertes Netz (nur GitHub o. ä.) braucht
  `pasta`/`slirp4netns` (beide fehlen) oder nftables (fehlt) → eigener Schritt.

**Folge für Ziel B:** Statt dauerhafter Linux-Benutzer je Projekt (Root-Helfer, sudoers, Aufräumen) schottet der
Kern jeden Agenten-Befehl in einer bwrap-Sandbox ab: sieht nur seinen Workspace beschreibbar, Geheimnisse und fremde
Projekte gar nicht. Kein Benutzer anlegen, keine Handarbeit, über Installer/Update schon verteilt. Erfüllt §2a.
Der „echte Benutzer je Projekt“ bleibt als spätere Stufe möglich, ist aber nicht mehr Voraussetzung.

## Wo starten Prozesse für Agenten (Kern)
| Stelle | Was | Heute |
|---|---|---|
| `tools/_launcher.py` (DevLauncher) | `shell_exec` auf dem Server | `bash` als `hydrahive`, voller Zugriff |
| `tools/_launcher_container.py` | `shell_exec` in Container-Projekten | `incus exec`, ohne Server-Umgebung – schon isoliert |
| `tools/_fs.py` | Datei-Werkzeuge (Container-Projekte über incus, sonst direkt) | direkt auf Platte, Pfadprüfung `safe_path` |
| `tools/web_browser.py:137` | Playwright-Browser | als `hydrahive` |
| `tools/code_graph_tools.py:36` | Code-Graph-Bau | als `hydrahive` |
| `tools/_document_process.py` | PDF/OCR | **schon bwrap** (Vorbild) |

Modul-Dienste mit eigenen Prozessen (vibe, archiver, videoeditor, studio, radiostream, hydralabor, tvwerkstatt,
tonstudio, opentor, diagramme, atelier, zerlegewerkstatt, vitrine, telephony, network) laufen als Dienst, nicht
direkt vom Agenten gesteuert – getrennt prüfen, nicht Teil von Etappe B2.

## Container-Modus existiert schon
`projects.execution = {"mode":"container", …}` (Spec `docs/specs/projekt-container-ausfuehrung.md`): Befehle und
Dateien laufen in einem incus-Container, nur eine Allowlist von 14 Werkzeugen (`runner/_project_tool_scope.py:14`).
Genutzt von 2 der 20 Projekten (Hydra-Labor, test). **Nicht als allgemeine Lösung:** incus ist ein Zusatz-Modul
(standardmäßig AUS), unter WSL meist nicht verfügbar, und die Allowlist schneidet Module/ask_agent ab.

## Geheimnisse und Pfade
- Heute liest `hydrahive` alles: `/etc/hydrahive2/*` (u. a. `api_keys.json`, `archive-remote.json`), `/var/lib/
  hydrahive2/{credentials,.ssh,*.db}`, alle 20 Workspaces.
- Projekt-Workspace „Hydrahive DEV“: Schlüssel + alte SSH-Konfig mit Zugängen zu Workstation (till, hydra) und
  hydratest (joshua) **heute verschoben** nach `/var/lib/hydrahive2/.ssh-quarantaene-2026-11-23`.
- Symlink `_work → /srv/hh-arbeit/work/_work` (Arbeitsordner aller Worktrees, 20+ Unterordner, bis 632 MB) –
  muss in den Workspace (B3), sonst greift die Sandbox ins Leere bzw. sperrt die Arbeit.
- `.ssh/`, `id_*` in weiteren Workspaces: noch nicht geprüft (B3: Prüfskript über alle Workspaces).

## Was eine Sandbox mitbringen muss, damit Arbeit weiterläuft (für B2)
- Lesend: `/usr`, `/bin`, `/lib*`, `/etc` ohne `/etc/hydrahive2`, Repo-Checkouts im Workspace, Python/Node aus `/usr`.
- Schreibend: der eigene Workspace, eigenes `/tmp`, `HOME` im Workspace (`.home/`), Caches dort (npm, pip, uv).
- Netz: für git/gh/npm ci nötig → Etappe B4 (zuerst offen lassen, aber 192.168.0.0/16 u. a. sperren braucht
  nft/pasta; bis dahin bleibt die ssh-Wortliste aus #732 die Netzsperre).
- Umgebung: nur feste Liste + die per Credential eingespeisten Tokens für genau diesen Befehl (wie `_build_env`).
- Werkzeuge, die bewusst Server-Pfade lesen (Datamining, Medien, Hilfe, Memory), laufen im Kern-Prozess, nicht in
  der Sandbox – davon nicht betroffen; nur `shell_exec` + Datei-Werkzeuge + Browser + Code-Graph wandern hinein.

## Vorschlag Etappen (ersetzt B1/B2 im Ziel, Abnahme P1–P8 bleibt)
1. **B2a** `SandboxLauncher` (bwrap) für `shell_exec` von Projekt-Agenten/Spezialisten, hinter Schalter
   `HH_AGENT_SANDBOX` (Standard erst aus, nach Live-Test an). Buddy/Master unverändert.
2. **B3** Arbeitsordner in Workspaces (Symlink `_work` auflösen), HOME/Caches in den Workspace, Prüfskript gegen
   Geheimnisse/Symlinks nach außen.
3. **B2b** Datei-Werkzeuge, Browser, Code-Graph auf denselben Bereich beschränken (realpath gegen Workspace).
4. **B4** Netzfilter (pasta installieren lassen via Installer/Update oder nft) – Heimnetz zu, GitHub offen.
5. **B5** Buddy-Projektumschalter: im Projektkontext ebenfalls Sandbox.
6. **B6** Live-Abnahme P1–P8 (Angriff 20.11. + Download 22.11. nachstellen, auch verschleiert).
