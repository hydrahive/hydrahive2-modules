# Plan: Zerlege-Werkstatt – spezifizierten Einstieg benutzbar machen

## Ziel
Umsetzung der bereits freigegebenen SPEC.md §12: Projekt anhand seines Namens auswählen, Fall anlegen, Datei aufnehmen, passende Analyse starten und den Bericht lesen, ohne eine Projekt-ID kennen zu müssen. Netzwerk-/Autorisierungsfehler werden nicht als leere Fallakte dargestellt. Diese Etappe ersetzt keine fehlende Analysetiefe.

## Dateien
- `frontend/ZerlegewerkstattPage.tsx`: Projektliste laden, Projektwechsel und Fehlerzustände, geführter Einstieg.
- `frontend/ProjectPicker.tsx`: UI zur Projektwahl mit Laden-, Leer- und Fehlerzustand.
- `frontend/ProjectPicker.test.tsx`: Projektwahl und Status regressionssicher rendern.
- `frontend/index.tsx`: deutsche und englische Texte.

## Implementierungsreihenfolge

### Task 1: Projektwahl und klare Zustände
- [x] Render-Tests für Projektname statt ID, Ladezustand, Fehler und keine Projekte (RED).
- [x] Projektliste über `projectsApi.list()` (bereits bestehende Kern-API) laden; automatisch erstes verfügbares Projekt vorauswählen.
- [x] Projektwechsel setzt ausgewählten Fall, Bericht und Details zurück; veraltete Ladeergebnisse ignorieren.
- [x] Fehler beim Laden von Fällen und Bericht sichtbar statt „keine Fälle“ oder „kein Bericht“ (GREEN).
- [x] Frontendtests, Typprüfung, Diff und Review.

## Akzeptanzkriterien
- [ ] Kein manuelles Eintippen einer Projekt-ID.
- [ ] Projektname ist auswählbar, und das Fallformular erscheint nach Auswahl.
- [ ] Kein Projekt und API-Fehler sind voneinander unterscheidbar.
- [ ] Beim Projektwechsel erscheinen keine Falldaten aus dem zuvor ausgewählten Projekt.
- [ ] Der Einstieg führt von Fallanlage zu Dateiaufnahme/Analyse/Bericht.

## Nicht in diesem Plan
- REA-MCP-Server, neue REA-Befehle, freies Durchreichen von Kommandos.
- „Vollständig“ behaupten: Analyseumfang und Berichtstiefe sind eigene Etappen mit gesonderten Akzeptanztests.
