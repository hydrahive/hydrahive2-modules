# Plan: Zerlege-Werkstatt – belegte Ableitungen im Bericht

## Ziel
Die Berichtsteile „Abgeleitet“ und „Vermutet“ werden nicht mehr hart leer ausgegeben. Eine kleine, deterministische Regelschicht erzeugt nur konservative Aussagen aus normalisierten REA-Feldern und nennt die Evidence-ID. Keine LLM-Deutung und keine unbelegte Behauptung einer lokalen Schnittstelle.

## Dateien
- `backend/inferences.py`: Evidence-Quellen finden, konservative PCAP-/Importregeln.
- `backend/reports.py`: Ableitungen, Vermutungen und Belegverzeichnis zusammenführen.
- `tests/test_reports.py`, `tests/test_inferences.py`: positive und negative Regeln, Grenzen, Beleg-IDs.
- `frontend/api.ts`, `frontend/ReportPanel.tsx`, `frontend/i18n.*.ts`: Belegverzeichnis anzeigen.

## Implementierungsreihenfolge
### Task 1: Regeln rot→grün
- [x] `.local`-DNS und RFC1918/link-local/loopback im eigenen Mitschnitt werden als lokale Kommunikationshinweise abgeleitet.
- [x] Windows-Netzwerkimporte erzeugen nur eine Vermutung über Netzwerkfähigkeit, keine Protokollbehauptung.
- [x] Öffentliche IPs, beliebige Strings und fehlende Evidence-ID erzeugen keine Ableitung.
- [x] Jede Aussage trägt die vollständige Evidence-ID; Ausgabe ist begrenzt und dedupliziert.

### Task 2: Bericht und Oberfläche
- [x] `reports.py` führt Regeln je abgeschlossenem Job aus und gibt ein Belegverzeichnis aus.
- [x] Oberfläche zeigt ID, Analysetyp, Operation und Confidence.
- [x] Regeltests und echter Bericht aus REA-PCAP-/PE-Ergebnissen grün; 137 Backend- und 14 Frontendtests, TypeScript, Ruff und Build grün.

## Akzeptanzkriterien
- [x] `derived`/`suspected` sind bei passenden Befunden gefüllt und sonst ehrlich leer.
- [x] Kein Bericht behauptet Protokoll oder lokale Steuerbarkeit allein wegen einer importierten Bibliothek.
- [x] Aussage und Beleg sind im Browser mit dem aktuellen 0.2.0-Frontend nachvollziehbar.
- [ ] 0.2.0 wird nach Merge über den normalen Modul-Installer aktualisiert und als installierter Stand erneut geprüft.
