---
name: diagramme
description: Interaktive Diagramme erstellen (Ablauf, Aufbau, Datenbank, Zustände, Zeitleiste) oder eine Antwort-Seite – bedienbar im Chat, dauerhaft gespeichert.
when_to_use: Wenn ein Plan, Ablauf, Aufbau, Befund oder Vergleich als Überblick hilft, wenn der Nutzer „zeig mir“, „mach mir einen Überblick“, „Diagramm“ oder „Schaubild“ sagt, oder bei Code-Architektur eines Repos. Nicht bei jeder Antwort.
tools_required: [diagramm_erstellen, diagramm_hilfe]
---

# Diagramme

Mit `diagramm_erstellen` entsteht ein interaktives Diagramm (Archify). Es wird **immer gespeichert** und erscheint
bedienbar im Chat und im Menü „Diagramme“.

## Ablauf
1. Passende Art wählen. Unsicher → `diagramm_hilfe` ohne `art`.
2. `diagramm_hilfe` mit `art` → Schema, Beispiel, Hinweise. **Schema lesen**, das Beispiel nur als Muster nehmen.
3. Vollständige Beschreibung schreiben (eigene IDs, deutsche Texte, `meta.locale` "en", `meta.quality_profile` "showcase").
4. `diagramm_erstellen` mit `art` und `beschreibung`.
5. Fehler? Die Hinweise von Archify (Code, Stelle, Vorschlag) gezielt umsetzen. **Höchstens 3 Versuche**, danach dem
   Nutzer sagen, was nicht klappt.

## Ändern
`diagramm_erstellen` mit `ersetzt=<ID>`: neue Fassung, die alte bleibt zum Nachschlagen.

## Aus Code
Bei einem Repo im Projekt `repo=<Ordner>` angeben und je Kasten `sources` (Datei, Zeilen) setzen – nur Stellen, die du
wirklich gelesen hast.

## Wann nicht
Kurze Antworten, einzelne Zahlen, reine Befehlsausgaben. Kein Diagramm, nur weil es geht.

Herkunft: gekürzt und übersetzt aus Archify `SKILL.md` (MIT, vendor/archify).
