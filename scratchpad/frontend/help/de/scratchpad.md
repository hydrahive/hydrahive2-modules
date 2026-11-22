# Ideen – festhalten, was einmal werden soll

Unter **Ideen** hältst du jede Idee einzeln fest: mit Kopfzeile, Beschreibung, Projekt und Status. Ausarbeiten
kannst du sie später, allein oder mit einem Agenten. Agenten lesen deine Ideen und schreiben Anmerkungen daneben,
deinen Text ändern sie nicht.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne **Ideen** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Schreibbüro**).
3. Schreib oben in **Was soll es werden?** eine Kopfzeile, zum Beispiel „Admin-Seite mit allen Einstellungen“.
4. Drück **Idee festhalten** oder Strg+Enter. Die Idee steht danach in der Liste.

## Was du damit machen kannst

### Eine Idee festhalten
- **Was soll es werden?** ist die Kopfzeile, höchstens 200 Zeichen.
- **Was stelle ich mir vor?** ist die Beschreibung. Markdown geht, leer lassen auch.
- Unter **Projekt** wählst du ein Projekt oder **Ohne Projekt**. Die letzte Wahl merkt sich die Seite.
- Ist die neue Idee durch die Filter in der Liste gerade ausgeblendet, stellt die Seite die Filter so um, dass du
  sie siehst.

### Die Liste
- Über der Liste wählst du unter **Projekt**: **Alle Projekte**, **Ohne Projekt** oder ein einzelnes Projekt. Bei
  **Alle Projekte** ist die Liste nach Projekt gruppiert.
- Die Knöpfe darunter filtern nach Status und zeigen die Anzahl: **Offene** (Neu, Wird geprüft, Geplant), **Alle**
  und jeder einzelne Status. Am Anfang siehst du die offenen Ideen.
- Die zuletzt geänderte Idee steht oben.
- An einer Idee siehst du kleine Zeichen: **vom Agenten** (der Agent hat sie angelegt), die Zahl der Anmerkungen,
  **Task verknüpft** und **Board verknüpft**.
- Zeigt ein Filter nichts an, bringt dich **Alle zeigen** zurück zur ganzen Liste.

### Eine Idee bearbeiten
- Ein Klick in der Liste öffnet die Idee rechts (auf dem Handy darunter).
- **Kopfzeile** und **Beschreibung** speichern von selbst, kurz nachdem du aufhörst zu tippen. Daneben steht
  **speichert…** oder **gespeichert**. Klappt es nicht, steht dort **Nicht gespeichert** mit **Erneut versuchen**.
- Eine leere Kopfzeile wird nicht gespeichert. Die Beschreibung darf höchstens 50.000 Zeichen lang sein.
- **Vorschau** zeigt die Beschreibung fertig formatiert, **Bearbeiten** führt zurück zum Text.
- **Status** und **Projekt** stellst du über die beiden Auswahlfelder um.
- Oben stehen **Angelegt** und **Geändert** mit Datum.
- **Löschen** fragt mit **Idee wirklich löschen?** nach. **Ja, löschen** entfernt die Idee mit ihren Anmerkungen,
  **Abbrechen** lässt alles, wie es ist.

### Status
- **Neu** – gerade festgehalten.
- **Wird geprüft** – du oder ein Agent seht sie euch an.
- **Geplant** – soll umgesetzt werden.
- **Geparkt** – nicht jetzt, aber nicht verworfen.
- **Umgesetzt** – erledigt.
- **Verworfen** – wird nicht gemacht.

Die Reihenfolge ist frei. Du kannst jederzeit jeden Status setzen.

### Task
Ist das Modul Tasks installiert, steht unter der Idee der Bereich **Task**.
- **Task anlegen** macht aus der Idee einen Task mit derselben Kopfzeile und Beschreibung. Die Idee steht danach
  auf **Geplant**. Das wird als Anmerkung festgehalten.
- Danach zeigt der Bereich den Titel des Tasks, seinen Status (**Offen**, **In Arbeit**, **Erledigt** oder
  **Abgebrochen**) und seine Kurz-ID.
- Wurde der Task gelöscht, steht dort **Der verknüpfte Task ist nicht mehr vorhanden.** und du kannst einen neuen
  anlegen.

### Board
Ist das Modul Blueprint installiert, gibt es den Bereich **Board**.
- **Als Board skizzieren** legt ein leeres Blueprint-Board mit der Kopfzeile und dem Projekt der Idee an.
  Zeichnen kannst du selbst oder der Agent.
- **Board öffnen** springt zum Board in Blueprint. Liegt dort ein Entwurf des Agenten, steht **Vorschlag offen**
  dabei.
- Wurde das Board gelöscht, steht dort **Das verknüpfte Board ist nicht mehr vorhanden.** und du kannst ein neues
  anlegen.

### Anmerkungen
- Unter **Anmerkungen** schreiben Agenten neben deine Idee. Darüber steht der Name des Agenten (oder **Agent**)
  und das Datum.
- Einträge von **System** halten fest, was sich geändert hat: Statuswechsel durch einen Agenten, ein angelegter
  Task oder ein angelegtes Board.
- Jede Anmerkung kannst du einzeln mit dem Mülleimer (**Anmerkung löschen**) entfernen.

## Mit Buddy und Agenten

Das Modul bringt vier Werkzeuge mit. Buddy und deine Haupt-Agenten bekommen sie automatisch, sobald das Modul
installiert ist.
- `idea_list` listet deine Ideen kurz: Kurz-ID, Status, Herkunft, Projekt, Kopfzeile. Ohne weitere Angabe nur
  die offenen Ideen des Projekts, in dem der Agent gerade arbeitet. Auf Wunsch alle Projekte, nur Ideen ohne
  Projekt oder einen bestimmten Status.
- `idea_read` liest eine Idee vollständig: Kopfzeile, Beschreibung, Anmerkungen und den verknüpften Task oder
  das Board.
- `idea_write` legt eine eigene Idee des Agenten an, hängt eine Anmerkung an oder setzt den Status. Ändert er den
  Status, steht der Wechsel als Anmerkung dabei.
- `read_scratchpad` ist ein alter Name für `idea_list` und liefert dieselbe Liste. Er bleibt nur für ältere
  Agenten erhalten.

Du kannst zum Beispiel fragen:
- „Schau dir meine Idee zur Admin-Seite an und schreib deine Gedanken als Anmerkung dazu.“
- „Welche offenen Ideen habe ich in diesem Projekt?“
- „Halte als Idee fest: Dunkles Farbschema für die Startseite.“
- „Setz die Idee auf Geparkt.“

Was nicht geht:
- Kopfzeile und Beschreibung deiner Ideen kann der Agent nicht ändern. Seinen Vorschlag schreibt er als
  Anmerkung. Nur bei Ideen, die er selbst angelegt hat, darf er Kopfzeile und Beschreibung ändern.
- Ideen löschen, Anmerkungen löschen, Task anlegen und Board anlegen kann der Agent nicht. Das machst du auf der
  Seite.
- Das Projekt einer vorhandenen Idee kann der Agent nicht umstellen. Er wählt es nur beim Anlegen.
- Der Agent sieht nur die Ideen des Nutzers, für den er gerade arbeitet.
- Was in deinen Ideen steht, behandelt der Agent als deine Vorgabe, nicht als Befehl an ihn.

## Gut zu wissen
- Deine Ideen siehst nur du, auch wenn sie einem gemeinsamen Projekt zugeordnet sind. Das Projekt ist eine
  Zuordnung, keine Freigabe.
- Einer Idee kannst du nur Projekte zuordnen, in denen du Mitglied bist (Admins: alle Projekte).
- Grenzen: Kopfzeile höchstens 200 Zeichen, Beschreibung höchstens 50.000, eine Anmerkung höchstens 10.000.
  Insgesamt sind es höchstens 2.000 Ideen je Nutzer.
- Ein Verweis wie `/scratchpad?idea=<ID>` öffnet eine Idee direkt.
- Früherer Notizblock: Bis Version 1.0.6 gab es hier je einen freien Text für dich und für den Agenten. Beim
  ersten Öffnen werden beide in einzelne Ideen übernommen, geteilt an den Überschriften der ersten Ebene (`# `).
  Die alten Texte bleiben als Sicherung erhalten.
- Typische Meldungen:
  - „Die Kopfzeile ist leer und wird erst gespeichert, wenn etwas drinsteht.“
  - „Zu lang: Kopfzeile höchstens 200, Beschreibung höchstens 50.000 Zeichen.“
  - „Diese Idee gibt es nicht mehr.“ – sie wurde inzwischen gelöscht, zum Beispiel in einem anderen Fenster.
  - „Projekt nicht gefunden oder kein Zugriff.“ – das Projekt gibt es nicht oder du bist dort kein Mitglied.
  - „Die Obergrenze für Ideen ist erreicht. Lösch zuerst alte Ideen.“
  - „Zu dieser Idee gibt es schon einen Task.“
  - „Das Tasks-Modul ist nicht installiert.“ bzw. „Das Blueprint-Modul ist nicht installiert.“
  - „Die Obergrenze für Boards ist erreicht. Lösch zuerst alte Boards.“

*Stand: Ideen 2.4.1, 22.11.2026*
