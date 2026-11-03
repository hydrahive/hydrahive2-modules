# Plan: Zerlege-Werkstatt – Firmware-Regionsinventur

## Ziel
Firmware-Artefakte erhalten eine eigene statische Signatur- und Regionsinventur über REA `inspect-firmware-regions` und Binwalk 3.1.0. Die Analyse meldet nur Kandidaten, Offsets, Längen und Beschreibungen; sie extrahiert nichts und führt nichts aus.

## Designentscheidung

- **Gewählt:** das veröffentlichte Binwalk-3.1.0-Crate mit festem SHA-256 laden, mit dem offiziellen Rust-1.81.0-Toolchain für x86_64/ARM64 (jeweils fester SHA-256) und `cargo --locked` bauen und als feste absolute Runtime-Abhängigkeit bereitstellen. Für SquashFS wird das von Binwalk 3.1.0 selbst referenzierte Sasquatch-Release `sasquatch-v4.5.1-4` architekturspezifisch und mit festen SHA-256 installiert.
- **Verworfen:** Ubuntu-Binwalk 2.x, weil REA 6.8.0 ausschließlich Binwalk 3.1.x akzeptiert.
- **Verworfen:** eigener Signatur-Scanner, weil er den geprüften REA/Binwalk-Vertrag unvollständig nachbauen würde.

## Dateien

- `backend/analysis_types.py` – fester Analysetyp ausschließlich für `firmware`.
- `backend/runtime.py` – feste `REA_BINWALK_COMMAND`-Umgebungsvariable.
- `extension/install.sh` – gepinntes Crate laden, prüfen, mit gesperrtem Lockfile bauen und Installation verifizieren.
- `frontend/api.ts`, `frontend/ui.ts`, `frontend/i18n.de.ts`, `frontend/i18n.en.ts` – synchroner Typ, Gruppe und verständliches Label.
- `tests/test_analysis.py`, `tests/test_runtime.py`, `tests/test_installer.py`, `tests/test_tools.py`, `frontend/analysisGroups.test.ts` – Vertrag, Positiv-/Negativgrenze, Runtime und Installer.
- `manifest.json` – Version 0.3.0.

## Implementierungsreihenfolge

### Task 1: Vertrag und Sicherheitsgrenze
- [x] Tests schreiben: `inspect-firmware-regions` fehlt; nur `firmware` ist zulässig, PE/ELF/APK sind unzulässig.
- [x] Tests rot ausführen.
- [x] Backend-, Agenten- und Frontend-Literalvertrag ergänzen.
- [x] Tests grün ausführen.

### Task 2: Gepinnte Binwalk-Abhängigkeit
- [x] Installer-Test schreiben: Version 3.1.0, Crate-SHA-256, `cargo --locked`, absoluter Laufzeitpfad und Versionsprüfung sind Pflicht.
- [x] Test rot ausführen.
- [x] Crate `binwalk-3.1.0.crate` mit SHA-256 `99d5dc70f5021c55624f098adae4d1de9c1c07d000475664704b675aad7e0811`, Rust 1.81.0 und Sasquatch `sasquatch-v4.5.1-4` mit architekturspezifischen SHA-256 installieren.
- [x] Runtime setzt ausschließlich `REA_BINWALK_COMMAND=/opt/binwalk/bin/binwalk`.
- [x] Tests grün ausführen.

### Task 3: Echte Offline-Abnahme
- [x] Deterministische synthetische Firmware mit eingebettetem SquashFS-Dateisystem erstellen.
- [x] Vollständiger `IncusRuntime`-Lauf liefert Binwalk-3.1.0-Evidence und mindestens einen Regionskandidaten.
- [x] Prozess läuft als `rea` ohne Capabilities; Container ist vorher und nachher offline; Arbeitsordner wird entfernt.
- [x] Negativfall: derselbe Typ wird für PE/ELF/API abgelehnt.
- [x] Vollständige Backend-/Frontend-Suite, TypeScript, Ruff, Shellsyntax und Produktionsbuild grün.

## Akzeptanzkriterien

- [x] Firmware zeigt „Firmware-Regionen prüfen“ in der Gruppe „Aufbau“.
- [x] Andere Artefakttypen zeigen diese Analyse nicht.
- [x] Kein freier Befehl, keine freie Option und kein Extraktionspfad gelangt aus API, UI oder Agentenwerkzeug zu REA.
- [x] Binwalk-Version und Quellpaket sind reproduzierbar festgelegt.
- [x] Ergebnis enthält nur statische Kandidaten und behauptet keine verifizierte Dateisystemgrenze ohne Beleg.

## Reale Abnahme am 03.11.2026

- Frischer Incus-Testklon `hh-zw-fwtest`, nach der Abnahme vollständig entfernt.
- Installiert und geprüft: Binwalk 3.1.0, Rust 1.81.0 und das gepinnte Sasquatch-DEB.
- Synthetisches, 8 KiB großes Firmware-Image mit eingebettetem SquashFS: Signatur bei Offset `0x1000`, gemeldete Größe 462 Byte.
- Direkter Binwalk-Test extrahierte über Sasquatch rekursiv `bin/startup` und `etc/release`; der öffentliche E2-Analysetyp bleibt absichtlich ein reiner Signatur-Scan.
- Vollständiger `IncusRuntime`-Lauf: Exit-Code 0, kein Timeout, Provider `binwalk` 3.1.0, normalisierte SquashFS-Region bei Offset 4096.
- Nachkontrolle: Container offline, temporärer Runtime-Arbeitsordner entfernt, kein Testklon oder Testartefakt verblieben.
- Prüfmatrix: 141 Backendtests, 15 Frontendtests, TypeScript, Ruff, Shellsyntax und Vite-Produktionsbuild grün.

## Nicht in diesem Plan

- Firmware-Extraktion (`extract-firmware`) oder Unblob als öffentlicher Analysetyp.
- Dateisystem-Mounts, Emulation, QEMU, Gerätezugriff oder Zielausführung.
- Neue Uploadtypen; bestehendes `firmware` bleibt die einzige Zulassung.
