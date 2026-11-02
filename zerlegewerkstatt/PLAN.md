# Plan: Zerlege-Werkstatt E1

## Ziel

Ein installierbares HydraHive-Modul mit Fallakten, sicheren Uploads/Samba-Eingang, isolierter statischer Analyse, drei kleinen Agentenwerkzeugen und einer Cockpit-Seite.

## Dateien

- `manifest.json` — Modulmetadaten, Berechtigung, Service/Installer.
- `SPEC.md` — verbindliche Sicherheits- und Produktanforderungen.
- `migrations/001_zerlegewerkstatt.sql` — Fälle, Artefakte, Jobs.
- `backend/__init__.py` — Registrierung von Router, Migrationen, Werkzeugen und Aufräumjob.
- `backend/models.py` — IDs, Zustände, Eingabeschemas und Fehlercodes.
- `backend/store.py` — parametrisierte DB-Zugriffe und Projektzugriff.
- `backend/files.py` — Fallbaum, atomare Writes, sichere Löschung.
- `backend/uploads.py` — Streaming, Typprüfung, Hash, Grenzen.
- `backend/intake.py` — Samba-Eingang ohne Symlinks/TOCTOU.
- `backend/runtime.py` — Incus-Status und feste Analysebefehle.
- `backend/jobs.py` — serielle Jobausführung und Neustart-Recovery.
- `backend/reports.py` — kleine normalisierte Berichte.
- `backend/routes.py` — authentifizierte REST-Routen.
- `backend/tools/*.py` — drei Agentenwerkzeuge ohne Pfad-/Befehlsparameter.
- `extension/install.sh` / `uninstall.sh` — gepinnter Containeraufbau bzw. Stoppen; Daten bleiben.
- `frontend/*` — Fallliste, Anlage, Upload, Artefakte, Jobs, Bericht.
- `tests/*` — isolierte Backendtests und Sicherheitsregressionen.

## Implementierungsreihenfolge

### Task 1: Modulgerüst und Falldaten
- [x] Tests für Manifest, Schema, Fallanlage, Projektzugriff und stabile Fehlercodes schreiben.
- [x] Tests rot ausführen.
- [x] Manifest, Migration, Modelle, Store und Basisrouten implementieren.
- [x] Tests grün ausführen.
- [x] Commit: `feat(zerlegewerkstatt): Fallakten und Berechtigungsgrenze`

### Task 2: Sicherer Web-Upload
- [x] Tests für Magic-Typen, Hash, leere Datei, Namen/Traversal, Teil-Datei, 512-MiB-Grenze, 2-GiB-Fallgrenze und atomare Veröffentlichung schreiben.
- [x] Tests rot ausführen.
- [x] Upload-Streaming und Dateispeicher implementieren.
- [x] Tests grün ausführen.
- [x] Security-Audit gegen Spec §6/§7.
- [x] Commit: `feat(zerlegewerkstatt): sichere Artefaktaufnahme`

### Task 3: Samba-Eingang
- [x] Tests für nur direkte reguläre Dateien, Symlink-Ablehnung, Dateiänderung während Aufnahme und unverändertes Original schreiben.
- [x] Tests rot ausführen.
- [x] Intake-Scanner und API implementieren.
- [x] Tests grün ausführen.
- [x] Commit: `feat(zerlegewerkstatt): Projekt-Samba-Eingang`

### Task 4: Isolierter Analyseadapter und Jobs
- [x] Tests für Positivliste, Argumentliste ohne Shell, Container-down, Zeitlimit, Abbruch, Outputgrenze, Recovery `running → interrupted` und doppelte Jobs schreiben.
- [x] Tests rot ausführen.
- [x] Incus-Adapter, Worker, Status und Berichtsnormalisierung implementieren.
- [x] Tests grün ausführen.
- [x] E0-Dateien als Fixtures durch den echten Container prüfen.
- [x] Security-Audit gegen Host-Secrets, Netz und Prozessreste.
- [x] Commit: `feat(zerlegewerkstatt): isolierte statische Analyse`

### Task 5: Drei Agentenwerkzeuge
- [x] Tests für Projektbindung, fehlende Berechtigung, keine Pfade/Befehle und begrenzte `untrusted_target_content`-Ausgabe schreiben.
- [x] Tests rot ausführen.
- [x] `reverse_cases`, `reverse_inspect`, `reverse_report` implementieren.
- [x] Tests grün ausführen.
- [x] Commit: `feat(zerlegewerkstatt): begrenzte Agentenwerkzeuge`

### Task 6: Cockpit
- [x] Frontendtests für Anlage, Pflichtbestätigung, Upload, Samba-Hinweis, Analyse, Fortschritt, Fehler und Bericht schreiben.
- [x] Tests rot ausführen.
- [x] API-Client und Seite implementieren.
- [x] `altlook.test.ts` und `farbstufen.test.ts` ergänzen.
- [x] Tests und Kern-Frontend-Build grün ausführen.
- [x] Commit: `feat(zerlegewerkstatt): Fallakten im Cockpit`

### Task 7: Reproduzierbarer Container-Installer
- [x] Script-Tests für feste Versionen/Hashes, unprivilegierten Container, Ressourcenlimits, minimale AppArmor-Regeln, fehlenden Incus-Fall, idempotentes Update und Datenbestand schreiben.
- [x] Tests rot ausführen.
- [x] Install-/Uninstall-Skript implementieren.
- [x] In frischem Wegwerf-Container testen.
- [x] Commit: `feat(zerlegewerkstatt): reproduzierbare Analyseumgebung`

### Task 8: Abnahme
- [x] WLED-APK und Windows-OpenSSH-PE vollständig durch den Modulweg analysieren.
- [x] Keine Ausführung und keine Restprozesse belegen.
- [x] Backend- und Frontend-Suites, `check_test_safety.py`, Version-Bump, `hh-review` und Security-Audit ausführen.
- [x] Browser-Abnahme im Cockpit.
- [x] PR mit Messwerten, Grenzen und bekannten E2-Punkten.

## Stand 02.11.2026

PR #339 in `hydrahive2-modules`, Branch `feat/zerlegewerkstatt-e1`. Alle fünf CI-Checks grün: 116 Backendtests, 7 Frontendtests, `tsc`, Ruff, Isolationstest, Versionsprüfung.

E2E am echten Container: Windows-OpenSSH-PE in 2,3 s, WLED-APK in 6,7 s, beide mit Confidence `observed`. Nachkontrolle: kein Ziel ausgeführt, Netz während der Analyse aus, Arbeitsordner leer, keine Analyseprozesse zurück.

Vier Fehler fielen erst in der Abnahme auf und sind behoben:

1. Die Falldaten lagen unter `data_dir/modules/zerlegewerkstatt/`. Dort liegen die Moduldateien, die ein Update überschreibt — ein Neuinstallieren hätte alle Fälle gelöscht. Jetzt: `data_dir/zerlegewerkstatt/`.
2. Das Netz des Containers blieb nach einem Fehler ausgeschaltet. Der Adapter stellt es jetzt im `finally` wieder her.
3. `incus config device add` bekam die Gerätewerte als getrennte Argumente statt als `key=value`. Das Wiederanheimgeln scheiterte dadurch still.
4. `status()` prüfte das echte `incus`-Binary auch mit injiziertem Test-Runner. Die Suite brach in der CI ab, wo Incus fehlt.

### Offen für E2

- Binwalk-3.1-/Unblob-Firmwareextraktion
- Wechsel auf den REA-MCP-Server (braucht gemessene Schemagröße unter 20.000 Tokens und eine echte Tool-Positivliste)
- Ghidra-Tiefenanalyse über `analyze-ghidra` ist in der Positivliste, aber gegen die beiden E2E-Dateien nicht durchlaufen
- Die gemeinsame Projekt-Samba-Anmeldung bleibt eine bekannte Grenze


## Nicht in diesem Plan

- Firmware-Dateisystemextraktion mit Binwalk 3.1/Unblob.
- Live-Mitschnitt, Frida, ADB oder Gerätedebugging.
- Windows-Ausführung/VM.
- Automatisches Erzeugen oder Installieren einer Home-Assistant-Integration.
- Per-Nutzer-Samba-Konten.
