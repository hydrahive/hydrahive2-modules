# Plan Mailbox 0.5.0 – einklappbare Konten und Handbuch

Spec: `mailbox/SPEC.md` §6 · Freigabe Till 23.10.2026.

## Ziel

Die Ordner jedes Mailkontos sind beim ersten Öffnen eingeklappt. Jedes Konto lässt sich einzeln auf- und zuklappen; die Auswahl bleibt in diesem Browser erhalten. Die In-App-Hilfe erklärt die komplette aktuelle Bedienung der Mailbox und weist ehrlich darauf hin, dass die geplanten `mailbox_*`-Agentenwerkzeuge noch nicht verfügbar sind.

## Dateien

### Modul-Repository
- `mailbox/frontend/folderCollapse.ts` – robustes Lesen, Speichern und Umschalten der aufgeklappten Konto-IDs.
- `mailbox/frontend/folderCollapse.test.ts` – Erstzustand, Persistenz, ungültige Daten und Speicherfehler.
- `mailbox/frontend/FolderTree.tsx` – Konto-Kopf als zugänglicher Auf-/Zuklappschalter.
- `mailbox/frontend/MailboxView.test.tsx` – eingeklappte und gespeicherte Darstellung.
- `mailbox/frontend/i18n.ts` – deutsche und englische Beschriftungen.
- `mailbox/frontend/MailboxPage.tsx` – Hilfe-Knopf für das Mailbox-Handbuch.
- `mailbox/manifest.json` – Version 0.5.0.
- `mailbox/SPEC.md` – bestätigtes Verhalten festhalten.

### Core-Repository
- `frontend/src/i18n/help/loader.ts` – Hilfe-Thema `mailbox` registrieren.
- `frontend/src/i18n/help/de/mailbox.md` – deutsches Handbuch.
- `frontend/src/i18n/help/en/mailbox.md` – englisches Handbuch.
- `frontend/src/i18n/locales/de/help.json` – Handbuch-Eintrag.
- `frontend/src/i18n/locales/en/help.json` – Manual entry.

## Implementierungsreihenfolge

### Task 1: Persistenzlogik
- [ ] Tests für fehlenden/ungültigen Speicher, vorhandene Konto-IDs und Umschalten schreiben.
- [ ] Tests rot ausführen.
- [ ] Minimale Persistenzlogik implementieren.
- [ ] Tests grün ausführen.

### Task 2: Ordnerleiste
- [ ] Darstellungstest: Erstzustand eingeklappt, gespeichertes Konto aufgeklappt.
- [ ] Konto-Kopf mit Chevron, `aria-expanded` und `aria-controls` ergänzen.
- [ ] Auf-/Zuklappen je Konto mit Persistenz verbinden.
- [ ] Frontend-Tests grün ausführen.

### Task 3: In-App-Handbuch
- [ ] Hilfe-Knopf in der Mailbox ergänzen.
- [ ] `mailbox` als Hilfe-Thema registrieren.
- [ ] DE/EN-Artikel und Handbuch-Einträge ergänzen.
- [ ] TypeScript, Tests und Produktionsbuild ausführen.

### Task 4: Release
- [ ] Modul-Version 0.4.1 → 0.5.0.
- [ ] Strukturprüfung und vollständige betroffene Tests ausführen.
- [ ] Änderungen je Repository getrennt committen und pushen.

## Akzeptanzkriterien

- [ ] Beim ersten Öffnen sind alle Konten eingeklappt.
- [ ] Klick auf einen Konto-Kopf zeigt oder verbirgt nur dessen Ordner.
- [ ] Neu hinzugefügte Konten starten eingeklappt.
- [ ] Der Zustand bleibt nach Neuladen im selben Browser erhalten.
- [ ] Defekter oder nicht verfügbarer Browser-Speicher verhindert die Bedienung nicht.
- [ ] Die Oberfläche ist per `aria-expanded` verständlich bedienbar.
- [ ] Hilfe-Knopf öffnet ein vollständiges deutsches bzw. englisches Mailbox-Handbuch.
- [ ] Das Handbuch beschreibt Absendername/Signatur über das Zahnrad und nennt den tatsächlichen Stand der Agentenwerkzeuge.
- [ ] Manifest meldet Version 0.5.0.

## Nicht in diesem Plan

- Projektfreigaben, gemeinsame Konten und `mailbox_*`-Agentenwerkzeuge (M3).
- Agentenversand mit Bestätigung (M4).
- Serverübergreifende Synchronisierung des eingeklappten Zustands.
