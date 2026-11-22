# Tickets – interne Vorgänge mit Nummer, Zuständigkeit und Frist

Tickets ist das interne Ticketsystem deiner HydraHive-Instanz. Jeder Vorgang bekommt eine Nummer, einen Status,
eine Priorität mit Frist und auf Wunsch ein Team und eine zuständige Person. So geht im Chat nichts mehr verloren.
Tickets sind **Intern**: Alle angemeldeten Nutzer sehen sie, Außenstehende nicht.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne **Tickets** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Arbeiten mit Agenten**).
3. Klicke oben rechts auf **Neues Ticket**.
4. Gib einen **Titel** ein. **Beschreibung**, **Priorität** und **Kategorie** sind freiwillig.
5. Klicke auf **Ticket erstellen**. Das Ticket öffnet sich sofort und steht links im **Posteingang**.

## Was du damit machen kannst

### Übersicht oben
Fünf Kacheln zeigen dir die Lage auf einen Blick:
- **Offen**: alle Tickets, die noch nicht gelöst, geschlossen oder abgebrochen sind.
- **Überfällig**: laufende Tickets, deren Fälligkeit vorbei ist.
- **Bald fällig**: laufende Tickets, die in den nächsten 24 Stunden fällig werden.
- **Meine Tickets**: von dir angelegt oder dir zugewiesen.
- **Ohne Zuweisung**: Tickets ohne zuständige Person.

Die letzten beiden Kacheln zählen auch erledigte Tickets mit.

### Posteingang
Links stehen deine Tickets, das zuletzt geänderte oben. Jede Zeile zeigt Nummer, Titel, wer es angelegt hat,
Priorität, Status, Kategorie und Fälligkeit. Ist die Fälligkeit vorbei, wird das Datum orange.
- Das Suchfeld durchsucht Titel und Beschreibung.
- Mit **Alle Status** und **Alle Prioritäten** filterst du die Liste.
- Setzt du Häkchen vor mehrere Tickets, erscheint oben „… **ausgewählt**“. Über **Priorität ändern** stellst du die
  Priorität aller markierten Tickets auf einmal um. Tickets, die du nicht bearbeiten darfst, bleiben dabei unverändert.

### Gespeicherte Ansichten
Über dem Posteingang speicherst du deine aktuelle Suche und deine Filter: Namen bei **Name der Ansicht** eintragen und
auf das Plus (**Ansicht speichern**) klicken. Unter **Ansicht auswählen** holst du sie wieder. Der Papierkorb
(**Ansicht löschen**) entfernt die gewählte Ansicht. Ansichten, die du hier speicherst, sieht nur du.

### Ein Ticket
Oben stehen Nummer, Status, Priorität, Titel und Beschreibung, darunter **Anfragende Person**, **Team**, **Erstellt**
und gegebenenfalls die **Kategorie**.

Rechts unter **Ticket verwalten** änderst du:
- **Status**: **Offen**, **Triage**, **In Arbeit**, **Wartet**, **Gelöst**, **Geschlossen** oder **Abgebrochen**.
  Nicht jeder Sprung ist erlaubt:
  - **Offen** → **Triage**, **In Arbeit** oder **Abgebrochen**
  - **Triage** → **In Arbeit**, **Wartet** oder **Abgebrochen**
  - **In Arbeit** und **Wartet** → untereinander, **Gelöst** oder **Abgebrochen**
  - **Gelöst** → **Geschlossen** oder zurück auf **In Arbeit**
  - **Geschlossen** und **Abgebrochen** → wieder **Offen**
- **Priorität**: **Niedrig**, **Normal**, **Hoch** oder **Dringend**. Die Frist wird dabei neu berechnet, solange du
  keine eigene Fälligkeit gesetzt hast.
- **Team**: eines der angelegten Teams oder **Nicht zugewiesen**.
- **Zugewiesen an**: die zuständige Person. Trag hier ihre **User-ID** ein (siehe „Gut zu wissen“). Gespeichert wird,
  sobald du das Feld verlässt.
- **Fälligkeit (manuell)**: ein eigenes Datum statt der Frist. Darunter steht, was gilt: **Manuelle Fälligkeit** oder
  **SLA-Fälligkeit**. **SLA-Berechnung wiederherstellen** nimmt deine eigene Fälligkeit wieder heraus.

Titel, Beschreibung und Kategorie lassen sich nach dem Anlegen in der Oberfläche nicht mehr ändern.

### Interner Verlauf
Hier schreibt ihr interne Kommentare. Text eingeben und auf den Pfeil (**Kommentieren**) klicken. Kommentare von Buddy
oder einem Agenten tragen das Zeichen **Agent**. Kommentare lassen sich nicht bearbeiten oder löschen.

### Anhänge
Mit **Anhang hinzufügen** lädst du eine Datei bis 25 MB hoch. Ein Klick auf einen Anhang lädt ihn herunter.

### Verknüpfungen
Gehört ein Ticket zu einem **Projekt**, einer **Task** oder einer **Session**, steht das hier. Diese Verknüpfungen
setzen Buddy und Agenten, zum Beispiel wenn sie ein Ticket aus einem Chat anlegen oder daraus eine Aufgabe machen.
Ein aus GitHub importiertes Ticket gehört automatisch zum Projekt der Verbindung. Von Hand setzen kannst du sie in der
Oberfläche nicht.

### Fristen und SLA-Profil
Jede Priorität hat eine Frist für die erste Reaktion und eine für die Lösung. Als Fälligkeit des Tickets gilt die
Lösungsfrist. Ab Werk gilt:

| Priorität | Erste Reaktion | Lösung |
|---|---|---|
| Dringend | 4 Stunden | 24 Stunden |
| Hoch | 8 Stunden | 72 Stunden |
| Normal | 24 Stunden | 120 Stunden |
| Niedrig | 72 Stunden | 240 Stunden |

Admins sehen links unten den Bereich **SLA-Profil**. Je Priorität gibt es zwei Felder in Stunden: das Feld mit dem
Namen der Priorität für die erste Reaktion und daneben **Lösung** für die Lösungsfrist. Danach **Speichern**. Die neuen Werte gelten für neue Tickets und für Tickets, deren
Frist neu berechnet wird.

### Teams
Links unten klappst du **Teams** auf. Admins legen mit **Teamname**, **Kurzbeschreibung (optional)** und dem Plus
(**Team anlegen**) ein Team an. Mitglieder kommen über das Feld **User-ID** und **Mitglied hinzufügen** dazu, das X
(**Mitglied entfernen**) nimmt sie wieder heraus. Über die Oberfläche kommen neue Mitglieder immer mit der Rolle
„member“ dazu. Mitglieder aufnehmen und entfernen dürfen Admins und die Leads des Teams.

### Benachrichtigungen
Die Glocke oben (**Benachrichtigungen**) zeigt die Zahl der ungelesenen Meldungen. Du bekommst eine Meldung, wenn bei
einem Ticket, das du angelegt hast, das dir zugewiesen ist oder das deinem Team gehört, etwas passiert. Ausgenommen
ist, was du selbst getan hast. Dazu kommen Erinnerungen bei bald fälligen und überfälligen Tickets und bei
überschrittenen Fristen. Ein Klick auf eine Meldung öffnet das Ticket und hakt die Meldung ab.

### GitHub-Projektintegration
Links unten verbindest du ein HydraHive-Projekt mit einem GitHub-Repository:
1. Wähle ein Projekt. Zur Auswahl stehen dessen GitHub-Repositories, für die im Projekt ein Git-Token hinterlegt ist.
2. Wähle bei **GitHub-Repository auswählen** das Repository und klicke **Verbindung hinzufügen**. Ist es schon
   verbunden, steht dort **Bereits verbunden**.
3. Leg für jede Verbindung fest, was HydraHive auf GitHub darf: **Nur lesen**, **Push** oder **Bidirektional**.
   **Push** und **Bidirektional** erlauben beide das Schreiben nach GitHub.
4. Der Papierkorb (**Verbindung deaktivieren**) schaltet eine Verbindung ab.

Dafür brauchst du Schreibrechte im Projekt.

### GitHub-Workbench
Der Knopf **GitHub-Workbench** oben schaltet zwischen Tickets und GitHub um. Wähle ein Projekt, die Verbindung
(**GitHub-Verbindung auswählen**), welche Issues du willst (**Offen**, **Geschlossen** oder **Alle**) und bei Bedarf
ein GitHub-Project (**GitHub-Project auswählen**).
- **Jetzt synchronisieren** holt die Issues von GitHub (höchstens 100) und legt für jedes noch nicht importierte Issue
  ein HydraHive-Ticket an, mit der Kategorie „github“ und im gewählten Projekt. Wurden Titel oder Beschreibung auf
  GitHub geändert, übernimmt der Abgleich das in die schon importierten Tickets. Die Listen füllen sich erst nach
  diesem Abgleich. Für den Abgleich brauchst du Schreibrechte im Projekt.
- Reiter **Issues**: oben die **GitHub-Issues** mit **Ticket öffnen** bzw. **Als Ticket importieren** und
  **Auf GitHub öffnen**. **Als Ticket importieren** startet denselben Abgleich wie **Jetzt synchronisieren** und öffnet
  danach das neue Ticket. Darunter die **HydraHive-Tickets** dieser Verbindung. Mit **Ins Project** nimmst du ein Issue
  in das gewählte GitHub-Project auf (nur mit **Push** oder **Bidirektional**).
- Reiter **Project-Board**: die Einträge des GitHub-Projects mit ihrem Status. Mit **Push** oder **Bidirektional**
  steht dort **Schreibzugriff aktiv** und du kannst den Status direkt umstellen, sonst steht dort **Nur lesen**.

### GitHub-Verknüpfung im Ticket
Gehört ein Ticket zu einem Projekt mit GitHub-Verbindung, verknüpfst du es im Ticket unter **GitHub-Verknüpfung** mit
einem Issue: Verbindung wählen, **Owner**, **Repository** und Issue-Nummer eintragen, dann **Issue verknüpfen**.
Ist die Verknüpfung da, schickt **Zu GitHub senden** Titel, Beschreibung und den Zustand offen oder geschlossen an das
Issue (nur mit **Push** oder **Bidirektional**). **Verknüpfung lösen** trennt Ticket und Issue wieder.

## Mit Buddy und Agenten

Ist das Modul installiert, bekommen Buddy und die anderen Hauptagenten diese Werkzeuge automatisch:
- `ticket_list` sucht und filtert Tickets, `ticket_read` liest ein Ticket mit Kommentaren, dem Änderungsprotokoll
  und den Namen der Anhänge.
- `ticket_create` legt ein Ticket an. Es wird automatisch mit dem Chat verknüpft und, im Chat eines Projekts, auch
  mit dem Projekt.
- `ticket_comment` schreibt einen Kommentar, `ticket_update` ändert unter anderem Titel, Beschreibung, Status,
  Priorität, Kategorie, Team oder Zuständigkeit.
- `ticket_create_task` macht aus einem Ticket eine verknüpfte Aufgabe. Dafür muss das Modul Aufgaben installiert sein.
  Pro Ticket geht das einmal.
- `ticket_github_read`, `ticket_github_link` und `ticket_github_unlink` lesen, setzen und lösen die
  GitHub-Verknüpfung eines Tickets. Verknüpft wird nur mit einem Issue aus einer eingerichteten Verbindung.
- `github_project_list` und `github_project_read` lesen GitHub-Projects und ihre Einträge. Diese beiden funktionieren
  nur im Chat eines Projekts und nur mit dessen Verbindungen.

Der Agent handelt mit deinen Rechten. Darfst du ein Ticket nicht bearbeiten, darf er es auch nicht.

Das kannst du zum Beispiel fragen:
- „Leg ein Ticket an: Login auf dem Tablet hängt, Priorität hoch.“
- „Welche offenen Tickets mit Priorität Dringend gibt es?“
- „Setz das Ticket zum Drucker im Büro auf In Arbeit und schreib als Kommentar, dass ich dran bin.“
- „Mach aus diesem Ticket eine Aufgabe für mich.“

Das geht nicht:
- Anhänge hochladen oder ihren Inhalt lesen. Der Agent sieht nur Name, Dateityp und Größe.
- Issues von GitHub importieren, synchronisieren oder Änderungen an GitHub senden.
- Teams, Mitglieder oder das SLA-Profil verwalten.
- Tickets löschen.

## Gut zu wissen

- Alle angemeldeten Nutzer können alle Tickets lesen und kommentieren. Bearbeiten dürfen: wer das Ticket angelegt
  hat, wem es zugewiesen ist, die Mitglieder seines Teams und Admins.
- Personen erscheinen als **User-ID** (eine interne Kennung), nicht als Name. Die User-ID einer Person siehst du zum
  Beispiel als **Anfragende Person** bei einem Ticket, das sie angelegt hat. Rechte und Benachrichtigungen greifen bei
  **Zugewiesen an** nur, wenn dort genau diese Kennung steht.
- Tickets, Kommentare und Anhänge lassen sich nicht löschen. Statt zu löschen setzt du ein Ticket auf
  **Abgebrochen** oder **Geschlossen**.
- Änderungen an einem Ticket werden im Hintergrund protokolliert. In der Oberfläche siehst du dieses Protokoll nicht,
  Buddy kann es mit `ticket_read` lesen.
- Der Posteingang zeigt höchstens die 50 zuletzt geänderten Tickets. Ältere findest du über Suche und Filter.
- Fristen laufen rund um die Uhr, auch nachts und am Wochenende.
- Erinnerungen zu Fristen entstehen, sobald jemand die Tickets-Seite öffnet oder dort ein Ticket ändert. Jede Erinnerung
  kommt pro Ticket nur einmal. Die Glocke lädt ihre Meldungen beim Öffnen der Seite. Die Meldungen tragen derzeit technische Kurznamen, zum Beispiel `ticket_updated`, `comment_added`,
  `overdue` oder `sla_resolution_breached`.
- Ob schon jemand reagiert hat, erfasst das Modul nicht. Die Erinnerung `sla_response_breached` (erste Reaktion
  überfällig) kommt deshalb nach Ablauf der Reaktionsfrist, auch wenn schon jemand kommentiert hat.
- Benachrichtigungen gibt es nur in HydraHive, nicht per Mail oder aufs Handy. Einen Mail-Eingang für Tickets gibt es
  nicht.
- GitHub nutzt den Git-Token, der im Projekt hinterlegt ist. Der Token wird in der Oberfläche nie angezeigt. Ein
  automatischer Abgleich mit GitHub läuft nicht, auch nicht mit **Bidirektional**. Neues holst du mit
  **Jetzt synchronisieren**.
- Das Modul selbst nutzt keine KI. Kosten entstehen nur, wenn du Buddy oder einen Agenten damit arbeiten lässt.
- Typische Meldungen:
  - **Änderung konnte nicht gespeichert werden.**: Der Statussprung ist nicht erlaubt oder du darfst das Ticket nicht
    bearbeiten.
  - **Anhang konnte nicht hochgeladen werden.**: zum Beispiel, weil die Datei größer als 25 MB ist.
  - **Team konnte nicht angelegt werden (Admin-Rechte erforderlich).**: Teams legen nur Admins an.
  - **Keine GitHub-Repositories mit Projekt-Token gefunden.**: Im Projekt fehlt ein GitHub-Repository mit Git-Token.
  - **Die Änderung konnte nicht zu GitHub synchronisiert werden.**: zum Beispiel, weil dir im Projekt Schreibrechte
    fehlen oder GitHub die Änderung abgelehnt hat.

*Stand: Tickets 0.9.5, 22.11.2026*
