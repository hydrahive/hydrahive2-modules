# Blueprint – Seiten und Abläufe skizzieren statt lange beschreiben

Blueprint ist eine Zeichenfläche für Ideen. Du ziehst Bausteine auf ein Board, beschriftest und verbindest sie.
So zeigst du einem Agenten, wie eine Seite aussehen oder ein Ablauf funktionieren soll, statt es mühsam zu
beschreiben. Umgekehrt kann der Agent dir einen Entwurf aufs Board legen, den du übernimmst oder verwirfst.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne **Blueprint** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Schreibbüro**).
3. Klicke links oben neben **Boards** auf das „+“ (**Neues Board**), gib einen Namen ein und drücke die
   Eingabetaste.
4. Zieh Bausteine aus der linken Leiste auf die Fläche. Ein Klick auf einen Baustein öffnet rechts seine Felder.
   Gespeichert wird von selbst.

## Was du damit machen kannst

### Boards
- Links stehen deine **Boards**, das zuletzt geänderte oben. Ein Klick öffnet eins.
- Hast du Projekte, gibt es darüber eine Auswahl: **Alle Projekte**, **Ohne Projekt** oder ein bestimmtes
  Projekt. Ist ein bestimmtes Projekt gewählt, gehört ein neues Board zu diesem Projekt, sonst zu keinem.
- Fährst du mit der Maus über ein Board, erscheint der Mülleimer (**Board löschen**). Vor dem Löschen fragt
  Blueprint nach. Mit dem Board gehen auch seine früheren Fassungen verloren.
- Ein kleines Funkel-Symbol am Board zeigt: **Vorschlag des Agenten offen**.
- Oben im Editor steht der Name des Boards und daneben, ob es **gespeichert** ist. Rechts daneben ordnest du das
  Board unter **Projekt** einem Projekt zu oder wählst **Ohne Projekt**. Zur Auswahl stehen die Projekte, die du
  sehen darfst.

### Die Zeichenfläche
- Die linke Leiste hat drei Gruppen:
  - **Layout** – wie eine Seite aussieht: **Seite**, **Karte / Box**, **Menü-Eintrag**, **Button**,
    **Eingabefeld**, **Schalter**, **Überschrift**, **Liste / Tabelle**.
  - **Funktion** – was passiert: **Event (Klick…)**, **Aktion**, **Datenquelle**, **Bedingung**, **Anzeige**,
    **Notiz**.
  - **Aufbau** – wie man es bauen könnte: **Modul**, **Schnittstelle**, **Datenbank / Tabelle**, **Datei**,
    **Agent-Werkzeug**.
- Verbinden: Zieh von einem Andockpunkt zum nächsten. Layout-Bausteine haben ihre Punkte oben und unten, alle
  anderen links und rechts. Eine **Bedingung** hat zwei Ausgänge, **ja** und **nein**. **Event (Klick…)** und
  **Notiz** haben keinen Eingang, **Anzeige** und **Notiz** keinen Ausgang.
- Ein angeklickter Baustein lässt sich an den Ecken größer und kleiner ziehen.
- Rechts bearbeitest du den angeklickten Baustein: **Beschriftung**, **Notiz an den Agenten** und beim
  **Eingabefeld** zusätzlich **Platzhalter**. Mit **Baustein löschen** oder der Rücktaste entfernst du ihn
  samt seinen Verbindungen.
- Unten gibt es Knöpfe zum Zoomen und eine kleine Übersichtskarte.

### Speichern und Abgleich
- Jede Änderung wird nach einem kurzen Moment gespeichert. Oben steht dann **gespeichert**, während des
  Speicherns **speichert…**.
- Solange das Fenster sichtbar ist, schaut Blueprint alle paar Sekunden nach Neuem. Legt ein Agent einen
  Vorschlag ab oder zeichnet auf dem Board, erscheint das ohne Neuladen.
- Hat jemand anderes das Board inzwischen geändert (der Agent oder ein zweites Fenster), während du ungespeicherte
  Änderungen hast, wird nichts überschrieben. Du wählst:
  - **Meine behalten** speichert deine Fassung und legt die andere zu den früheren Fassungen.
  - **Neue laden** zeigt die andere Fassung, deine ungespeicherten Änderungen entfallen.
- Klappt Speichern oder Laden nicht, hilft **Erneut versuchen**. Deine Änderungen bleiben so lange im Fenster.

### Vorschlag des Agenten
Hat der Agent einen Entwurf auf ein Board mit Inhalt gelegt, erscheint über der Fläche ein Band
**Vorschlag des Agenten**. Es zeigt Zeitpunkt, Zahl der Bausteine und Verbindungen, die Notiz des Agenten und
welche Bausteine neu sind oder entfallen.
- **Vorschau** zeigt den Vorschlag, neue Bausteine sind umrandet. Bearbeiten geht dort nicht.
  **Meine Fassung zeigen** schaltet zurück.
- **Übernehmen** ersetzt deine Fassung durch den Vorschlag. Deine bisherige Fassung bleibt unter
  **Frühere Fassungen** erhalten. Übernehmen geht erst, wenn deine Fassung gespeichert ist.
- **Verwerfen** löscht den Vorschlag. Deine Fassung bleibt, wie sie ist.

### Frühere Fassungen
Der Knopf **Frühere Fassungen** oben rechts öffnet die Liste, neueste zuerst. Jede Fassung zeigt Datum, Zahl der
Bausteine und wie sie entstanden ist: vor einem übernommenen Vorschlag, vor einem Wiederherstellen oder durch
„Meine behalten“ ersetzt. **Wiederherstellen** macht sie wieder zu deiner Fassung und sichert vorher deinen
aktuellen Stand. Je Board bleiben die letzten 20 Fassungen.

### Als Text kopieren
**Als Text kopieren** legt das Board als Text in die Zwischenablage: alle Bausteine mit Beschriftung, Platzhalter
und Notiz, dazu die Verbindungen, bei Bedingungen mit „ja“ und „nein“. Das ist derselbe Aufbau, den Agenten mit
ihrem Werkzeug lesen. Den Text kannst du in jeden Chat einfügen, auch bei Agenten ohne Blueprint-Werkzeuge.
In der Vorschau kopierst du den Vorschlag.

### Chat neben dem Board
Der Knopf **Agent** öffnet rechts den **Chat mit dem Agenten**. Dort antwortet der Agent des Projekts, zu dem
das Board gehört.
- Je Board gibt es eine eigene Unterhaltung. Sie bleibt erhalten, wenn du den Chat schließt und wieder öffnest.
- Der Agent weiß nicht von selbst, um welches Board es geht. Beim ersten Öffnen zeigt Blueprint einen
  Einstiegstext mit Name und Nummer des Boards. Kopiere ihn mit **Einstiegstext kopieren** und stell ihn deiner
  ersten Nachricht voran. **Einstiegstext zeigen** holt ihn später wieder hervor.
- Ist das Board mit einer Idee aus dem Modul Ideen verknüpft, nennt der Einstiegstext auch die Idee.
- Den Chat machst du an seinem linken Rand breiter oder schmaler. Ist das Fenster zu schmal, liegt der Chat über
  dem Board. Öffnest du dann **Frühere Fassungen** oder die **Vorschau**, macht er Platz.
- Keinen Chat gibt es, wenn das Board zu keinem Projekt gehört, das Projekt keinen Agenten hat oder du dort nur
  Leserecht hast. Blueprint sagt dir jeweils den Grund.

## Mit Buddy und Agenten

Agenten haben zwei Werkzeuge:

- `blueprint_read` zeigt die Liste deiner Boards oder liest ein Board als Text, gesucht nach Nummer oder Name.
  Der Agent liest immer deine Fassung. Liegt ein offener Vorschlag da, erfährt er das zusätzlich.
- `blueprint_propose` legt einen Entwurf ab. Der Agent liefert nur Bausteine und Verbindungen, die Anordnung
  entsteht von selbst: Layout links untereinander, Abläufe rechts daneben, Aufbau darunter.
  - Ein neues Board legt er mit Namen an und zeichnet direkt darauf. Es gehört zum Projekt der Unterhaltung,
    wenn du dieses Projekt sehen darfst.
  - Ein leeres Board zeichnet er direkt.
  - Hat das Board schon Inhalt, entsteht ein Vorschlag neben deiner Fassung. Du übernimmst oder verwirfst ihn.
    Ein neuer Vorschlag ersetzt einen älteren, noch offenen.
  - Danach bekommt der Agent einen Link, der das Board direkt öffnet, und kann ihn dir nennen.

Dein Buddy und andere Master-Agenten bekommen beide Werkzeuge automatisch. Das passiert beim Neustart des
Servers, den die Installation auslöst.
Anderen Agenten gibt ein Admin sie in den Agenten-Einstellungen im Reiter **Tools & MCP**. Fehlen sie dem
Projekt-Agenten im Chat neben dem Board, steht dort ein Hinweis. Ein Admin sieht dazu den Knopf
**Werkzeuge ergänzen**. Bei Agenten, die ein anderes Modul verwaltet, klappt das nicht.

Das kannst du zum Beispiel fragen:
- „Schau dir mein Board ‚Login-Seite‘ an und bau das so.“
- „Skizziere mir den Ablauf der Bestellung als neues Board.“
- „Überarbeite das Board ‚Startseite‘: Es fehlt ein Suchfeld.“

Das geht nicht:
- Agenten überschreiben deine Fassung nie. Auf einem Board mit Inhalt legen sie nur einen Vorschlag ab.
- Agenten können keine Boards löschen oder umbenennen, keinen Vorschlag übernehmen und keine frühere Fassung
  wiederherstellen. Das machst nur du im Board.
- Agenten sehen nur deine eigenen Boards, nie die anderer Nutzer.
- Ein Entwurf hat höchstens 80 Bausteine und 400 Verbindungen. Größeres muss der Agent aufteilen.

## Gut zu wissen

- Deine Boards gehören nur dir. Auch wenn ein Board einem Projekt zugeordnet ist, sehen andere Mitglieder es
  nicht. Das Projekt bestimmt nur, welcher Agent im Chat antwortet.
- Beschriftungen und Notizen gibt Blueprint dem Agenten ausdrücklich als deine Wünsche weiter, nicht als
  Anweisungen an das System.
- Kosten: Das Zeichnen selbst kostet nichts. Nur der Agent verbraucht beim Lesen und Entwerfen wie gewohnt Tokens.
- Grenzen: höchstens 200 Boards je Nutzer, Namen bis 120 Zeichen, ein Board bis 2 MB.
- Typische Meldungen:
  - „Die Obergrenze für Boards ist erreicht. Lösch zuerst alte Boards.“ – du hast 200 Boards.
  - „Das verlinkte Board gibt es nicht oder es gehört dir nicht.“ – der Link zeigt auf ein gelöschtes oder
    fremdes Board.
  - „Deine Fassung ist noch nicht gespeichert. …“ – erst speichern lassen, dann übernehmen oder wiederherstellen.
  - „Der Vorschlag hat sich inzwischen geändert. Schau ihn dir noch einmal an.“ – der Agent hat währenddessen
    einen neuen Vorschlag abgelegt.
  - „Der gespeicherte Inhalt dieses Boards ist nicht lesbar. …“ – Blueprint überschreibt ihn nicht. Übernimm einen
    Vorschlag oder stell eine frühere Fassung wieder her.
  - „Projekt nicht gefunden oder kein Zugriff.“ – das gewählte Projekt gibt es nicht oder du darfst es nicht
    sehen.

*Stand: Blueprint 1.3.1, 22.11.2026*
