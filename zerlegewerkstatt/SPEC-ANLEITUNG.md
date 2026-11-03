# Zerlege-Werkstatt – integrierte Benutzeranleitung

## Problem

Die Werkstatt bildet den technischen Analysevertrag korrekt ab, erklärt aber nicht, wie ein Nutzer ohne Reverse-Engineering-Vorwissen von einer Frage zu einem verständlichen Ergebnis gelangt. Feldnamen und Analyseknöpfe allein reichen nicht; Dateitypen, Fallstruktur, Analysegruppen, Belegstufen und Grenzen müssen im Arbeitskontext erklärt werden.

## Ziel

Jeder Nutzer soll direkt in der Werkstatt nachvollziehen können:

1. welches Material geeignet ist,
2. wie ein Fall sinnvoll formuliert wird,
3. wie Dateien aufgenommen und analysiert werden,
4. welche Analyse für welche Frage passt,
5. wie Bericht, Confidence und Beleg-ID zu lesen sind,
6. welche Aussagen die Werkstatt bewusst nicht treffen kann.

## UI-Entscheidung

Die Anleitung liegt direkt unter dem Seitenkopf und besteht aus zwei Ebenen:

- **Schnellstart:** sechs ständig sichtbare, kurze Arbeitsschritte.
- **Ausführliche Anleitung:** ein aufklappbarer Bereich mit thematischen Kapiteln und konkreten Beispielabläufen.

Kein separater externer Link, kein Wizard, der die eigentliche Arbeitsfläche blockiert, und keine vorausgesetzten Fachkenntnisse.

## Inhalte

### Grundlagen

- statische/offline Analyse statt Programmausführung,
- Projekt → Fall → Artefakt → Analyseauftrag → Bericht → Beleg,
- rechtliche Berechtigungsbestätigung und Herkunftsnotiz.

### Dateifamilien

- Windows PE (`.exe`, `.dll`),
- Android APK,
- Linux/Unix ELF,
- Firmware (`.bin`),
- passive Mitschnitte (`.pcap`, `.pcapng`).

### Analyseauswahl

Alle sichtbaren Analysearten werden in Alltagssprache erklärt. Nicht passende Analysen erscheinen nicht. Tiefenanalyse wird als langsamere, codeorientierte Ergänzung erklärt, nicht als pauschal bessere Wahl.

### Bericht lesen

- Beobachtet = direkt gemessen,
- Abgeleitet = regelbasiert aus Belegen geschlossen,
- Vermutet = plausible, noch unbestätigte Hypothese,
- Unbekannt = statisch nicht beantwortbar,
- Nächste erlaubte Prüfung = sicherer Folgeschritt,
- Beleg-ID, SHA-256, Engine und Confidence.

### Beispielabläufe

- Router-Firmware untersuchen,
- Windows-Programm auf lokale Kommunikation prüfen,
- Android-App und Signatur prüfen,
- eigenen PCAP-Mitschnitt auf Endpunkte/DNS/TLS prüfen.

### Fehlerhilfe

Erklärt unter anderem: unbekannter Dateityp, doppelte Datei, Analyse passt nicht, Auftrag wartet/läuft/ist unterbrochen, leerer Bericht und fehlender Beleg.

## Akzeptanzkriterien

- Schnellstart ist ohne zusätzlichen Klick sichtbar.
- Ausführliche Anleitung ist per klar beschriftetem Element erreichbar.
- Alle Texte sind auf Deutsch und Englisch verfügbar.
- Mindestens vier konkrete Beispielabläufe sind enthalten.
- Analysearten werden ohne interne REA-Befehlsnamen erklärt.
- Anleitung verspricht weder Ausführung, Emulation noch automatische Firmware-Extraktion.
- Frontendtests prüfen Sichtbarkeit, zentrale Begriffe und Aufklappstruktur.
- Mobile Breite erzeugt keinen horizontalen Überlauf.
