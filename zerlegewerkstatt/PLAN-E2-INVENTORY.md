# Plan: Zerlege-Werkstatt – tiefe Inventur vorhandener Dateiarten

## Ziel
Vorhandene PE-, ELF- und APK-Artefakte fachlich untersuchen können, statt nur einen allgemeinen REA-Überblick zu erhalten. Alle neuen Funktionen bleiben feste, parameterlose HydraHive-Analysetypen; Zielcode wird nicht ausgeführt.

## Dateien
- `backend/analysis_types.py`: elf feste CLI-Zuordnungen, Dateigrenzen und kompakte Evidence-Ausgabe.
- `frontend/api.ts`, `frontend/ui.ts`: synchroner Typvertrag und fachliche Gruppen.
- `frontend/ArtifactPanel.tsx`: gruppierte statt ungeordnete Analyseknöpfe.
- `frontend/i18n*.ts`: verständliche Labels, nach Sprachen aufgeteilt.
- `tests/test_analysis.py`, `tests/test_tools.py`, `frontend/analysisGroups.test.ts`: Positivliste, Agentenschema und UI-Zuordnung.
- `manifest.json`, `tests/test_installer.py`: Version 0.2.0.

## Implementierungsreihenfolge

### Task 1: Vertrag und Sicherheitsgrenzen
- [x] Tests rot: neue Typen fehlen in Positivliste und Agentenschema.
- [x] Typen auf passende Artefakte begrenzen; keine freien Parameter.
- [x] Große Resultate als Summary plus vollständiges Evidence-Bundle speichern.
- [x] Entropie-Blöcke fest auf 64 KiB setzen, um Ausgaben zu begrenzen.

### Task 2: Fachliche Oberfläche
- [x] Analysen in Überblick, Aufbau, Code/Abhängigkeiten, Netzwerk und Signaturen gruppieren.
- [x] Nicht passende Analysen ausblenden.
- [x] Übersetzungen auf Dateien unter 200 Zeilen aufteilen.

### Task 3: Echte Abnahme
- [x] PE/CLI: Entropie, Imports, Ressourcen, Load-Config und Zertifikatstabelle.
- [x] ELF: Exporte, Notes, Go, Rust und Kernelmodul-Metadaten.
- [x] APK: Signaturschemata/Signierer/Digests an offizieller WLED-App.
- [x] Alle elf Läufe durch `IncusRuntime`: offline, `rea`, keine Capabilities, Aufräumen und Netz-Wiederherstellung.
- [x] Vollständige Suite nach letztem Diff: 131 Backendtests, 13 Frontendtests, TypeScript, Ruff und Produktionsbuild grün.
- [ ] Unabhängiges Review nach letztem Diff.

## Akzeptanzkriterien
- [x] Insgesamt 17 feste native Analysetypen statt vier.
- [x] Elf neue Typen liefern am echten Artefakt gültiges JSON bzw. Evidence.
- [x] Agentenwerkzeug und REST-API teilen denselben Literal-Vertrag.
- [x] Kein MCP, keine freie REA-Unterbefehls- oder Optionswahl.
- [ ] Installierte 0.2.0 im Browser durchspielen.

## Nicht in diesem Plan
- Binwalk/Firmware-Regionen (REA verlangt einen separat gepinnten Binwalk-Pfad).
- Pwntools-Binary-Layout, neue Uploadformate, parameterisierte Tiefenanalyse.
- Ableitungsregeln des Berichts; eigene folgende Etappe.
