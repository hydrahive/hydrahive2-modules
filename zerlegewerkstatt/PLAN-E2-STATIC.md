# Plan: Zerlege-Werkstatt – statische Analysen aus SPEC §7 vervollständigen

## Ziel
Zwei in SPEC.md §7 ausdrücklich vorgesehene, aber bisher fehlende native Analysearten wirklich zugänglich machen: .NET-Mitglieder und passive PCAP-/PCAPNG-Inventur. REA 6.8.0 bestätigt für beide einen CLI-Aufruf mit lokalem Dateipfad und `--format json`. Kein REA-MCP und keine freie Befehlsübergabe.

## Dateien
- `backend/analysis_types.py`: feste Positivliste, Artefaktgrenzen und begrenztes .NET-Evidence-Bundle.
- `tests/test_analysis.py`, `tests/test_runtime.py`: Zulässigkeit, Offline-Argumentliste, CLI-Aufruf, Grenzen.
- `frontend/api.ts`, `frontend/ui.ts`, `frontend/index.tsx`: identische Typen und verständliche Analyseknöpfe.
- `manifest.json`, `tests/test_installer.py`: Version und Test aktualisieren.

## Implementierungsreihenfolge
### Task 1: Fehlende §7-Arten
- [x] Test rot: `inspect-managed-members` nur für `pe`, `inspect-pcap-capture` nur für `pcap`/`pcapng`; kein freier Befehl.
- [x] Zwei feste Argumentlisten ergänzen; .NET-Mitglieder `--detail summary` mit Evidence-Bundle (sonst beliebig große Ausgabe); PCAP-Inventur mit fest installiertem TShark/Capinfos und geprüftem Ausgabeadapter.
- [x] Frontend- und Backendtypen synchron halten; beide Analyseknöpfe anzeigen.
- [x] Unit-Suite, REA-CLI am Container mit echten zulässigen Beispieldateien, Prüfung der Belegausgabe.
- [x] Commit nach Review.

## Akzeptanzkriterien
- [ ] Nach Upload einer PE-/CLI-Datei stehen Mitglieder und Signaturen zur Analyse zur Verfügung; nicht bei APK.
- [ ] Nach Upload eines eigenen Mitschnitts lässt sich die passive PCAP-Inventur starten; nicht bei PE.
- [ ] REA wird im Container offline, ohne Shell und ohne Ausführung des Ziels aufgerufen.
- [ ] Ergebnis/Befunde lassen sich über die bestehende Fallakte lesen.

## Nicht in diesem Plan
- Unspezifizierte dynamische Instrumentierung, Browser-/ADB-Tools, Umgehung von Authentifizierung oder Schutzmaßnahmen, freier REA-Zugriff. Weitere statische REA-Arten werden erst nach Funktions-/Sicherheitsmatrix und abgestimmtem Umfang zugelassen.
