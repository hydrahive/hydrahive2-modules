---
name: vibe-regeln
description: So baut der Vibe-Agent in kleinen, prüfbaren Schritten eine App und hält die Projektregeln in VIBE.md ein.
when_to_use: Zu Beginn jeder Vibe-Sitzung und immer, wenn der Nutzer etwas an der App ändern, ergänzen oder reparieren will.
---

# Vibe-Regeln

## 1. Erst lesen

- `cat /work/VIBE.md` – das sind die Regeln des Nutzers. Halte dich daran.
- Bei einer neuen App ist die Datei fast leer. Beschreibe dort in ein paar Sätzen, was die App sein soll, sobald der
  Nutzer es dir gesagt hat.

## 2. Kleine Schritte

- Eine Änderung, dann die Vorschau prüfen. Nicht fünf Dinge auf einmal.
- Bevorzuge kleine Dateien. Teile Komponenten, bevor eine Datei lang wird.
- Neue Pakete nur, wenn es sich lohnt. Prüfe vorher, ob es auch ohne geht.

## 3. Jede Antwort beginnt mit einer Zeile

- Höchstens 100 Zeichen, in einfachen Worten, was sich geändert hat. Beispiel: „Knopf größer und blau gemacht“.
- Diese Zeile wird die Beschriftung der Version in der Zeitleiste.

## 4. Fehler

- Die Oberfläche meldet dir Fehler der App und des Entwicklungs-Servers.
- Behebe die Ursache, nicht nur das Symptom. Erkläre kurz, was kaputt war.
- Nach **3 Versuchen** ohne Erfolg: ehrlich sagen, dass du nicht weiterkommst, und den Nutzer bitten zu beschreiben,
  was er in der Vorschau sieht.

## 5. Sicherheit

- Keine Passwörter, Schlüssel oder Zugangsdaten in Dateien.
- Nur im Ordner `/work` arbeiten. Der Container ist abgeschottet. Das ist Absicht und wird nicht umgangen.
