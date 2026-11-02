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
- [ ] Tests für Manifest, Schema, Fallanlage, Projektzugriff und stabile Fehlercodes schreiben.
- [ ] Tests rot ausführen.
- [ ] Manifest, Migration, Modelle, Store und Basisrouten implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): Fallakten und Berechtigungsgrenze`

### Task 2: Sicherer Web-Upload
- [ ] Tests für Magic-Typen, Hash, leere Datei, Namen/Traversal, Teil-Datei, 512-MiB-Grenze, 2-GiB-Fallgrenze und atomare Veröffentlichung schreiben.
- [ ] Tests rot ausführen.
- [ ] Upload-Streaming und Dateispeicher implementieren.
- [ ] Tests grün ausführen.
- [ ] Security-Audit gegen Spec §6/§7.
- [ ] Commit: `feat(zerlegewerkstatt): sichere Artefaktaufnahme`

### Task 3: Samba-Eingang
- [ ] Tests für nur direkte reguläre Dateien, Symlink-Ablehnung, Dateiänderung während Aufnahme und unverändertes Original schreiben.
- [ ] Tests rot ausführen.
- [ ] Intake-Scanner und API implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): Projekt-Samba-Eingang`

### Task 4: Isolierter Analyseadapter und Jobs
- [ ] Tests für Positivliste, Argumentliste ohne Shell, Container-down, Zeitlimit, Abbruch, Outputgrenze, Recovery `running → interrupted` und doppelte Jobs schreiben.
- [ ] Tests rot ausführen.
- [ ] Incus-Adapter, Worker, Status und Berichtsnormalisierung implementieren.
- [ ] Tests grün ausführen.
- [ ] E0-Dateien als Fixtures durch den echten Container prüfen.
- [ ] Security-Audit gegen Host-Secrets, Netz und Prozessreste.
- [ ] Commit: `feat(zerlegewerkstatt): isolierte statische Analyse`

### Task 5: Drei Agentenwerkzeuge
- [ ] Tests für Projektbindung, fehlende Berechtigung, keine Pfade/Befehle und begrenzte `untrusted_target_content`-Ausgabe schreiben.
- [ ] Tests rot ausführen.
- [ ] `reverse_cases`, `reverse_inspect`, `reverse_report` implementieren.
- [ ] Tests grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): begrenzte Agentenwerkzeuge`

### Task 6: Cockpit
- [ ] Frontendtests für Anlage, Pflichtbestätigung, Upload, Samba-Hinweis, Analyse, Fortschritt, Fehler und Bericht schreiben.
- [ ] Tests rot ausführen.
- [ ] API-Client und Seite implementieren.
- [ ] `altlook.test.ts` und `farbstufen.test.ts` ergänzen.
- [ ] Tests und Kern-Frontend-Build grün ausführen.
- [ ] Commit: `feat(zerlegewerkstatt): Fallakten im Cockpit`

### Task 7: Reproduzierbarer Container-Installer
- [ ] Script-Tests für feste Versionen/Hashes, unprivilegierten Container, Ressourcenlimits, minimale AppArmor-Regeln, fehlenden Incus-Fall, idempotentes Update und Datenbestand schreiben.
- [ ] Tests rot ausführen.
- [ ] Install-/Uninstall-Skript implementieren.
- [ ] In frischem Wegwerf-Container testen.
- [ ] Commit: `feat(zerlegewerkstatt): reproduzierbare Analyseumgebung`

### Task 8: Abnahme
- [ ] WLED-APK und Windows-OpenSSH-PE vollständig durch den Modulweg analysieren.
- [ ] Keine Ausführung und keine Restprozesse belegen.
- [ ] Backend- und Frontend-Suites, `check_test_safety.py`, Version-Bump, `hh-review` und Security-Audit ausführen.
- [ ] Browser-Abnahme im Cockpit.
- [ ] PR mit Messwerten, Grenzen und bekannten E2-Punkten.

## Nicht in diesem Plan

- Firmware-Dateisystemextraktion mit Binwalk 3.1/Unblob.
- Live-Mitschnitt, Frida, ADB oder Gerätedebugging.
- Windows-Ausführung/VM.
- Automatisches Erzeugen oder Installieren einer Home-Assistant-Integration.
- Per-Nutzer-Samba-Konten.
