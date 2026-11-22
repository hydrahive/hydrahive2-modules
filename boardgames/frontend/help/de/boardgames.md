# Brettspiele – Schach spielen, zu zweit oder gegen Computer und KI-Modell

Brettspiele bringt klassische Brettspiele direkt in HydraHive. Heute gibt es **Schach**. Du spielst zu zweit an
einem Gerät, gegen den eingebauten Computer oder gegen ein KI-Modell, das du selbst auswählst. Das ist gut für
eine Pause oder um zu sehen, wie gut ein Modell Schach spielt.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne **Brettspiele** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Freizeit**).
3. Klicke auf die Kachel **Schach**. Das Spiel öffnet sich als großes Fenster über der Seite.
4. Wähle unter **Spielmodus wählen** einen Modus. Dann klickst du eine eigene Figur an und danach ein Zielfeld.

## Was du damit machen kannst

### Spielmodus wählen
- **2 Spieler (ein Gerät)** – ihr wechselt euch am selben Bildschirm ab. Weiß beginnt.
- **Gegen Computer** – du spielst Weiß, der Computer Schwarz. Unter dem Brett steht der Hinweis dazu.
- **Gegen ein KI-Modell** – ein Sprachmodell spielt Schwarz gegen dich. Erst wählst du unter **KI-Modell wählen**
  das Modell aus der Liste, dann klickst du **Partie starten**. Kostenlose Modelle sind mit „free“ markiert.
  Mit **Zurück** kommst du wieder zur Modus-Auswahl.

### Das Brett
- Klickst du eine eigene Figur an, wird ihr Feld blau. Grüne Punkte zeigen die erlaubten Zielfelder. Kann die
  Figur dort schlagen, ist das Feld rot umrandet.
- Der letzte Zug bleibt farbig markiert.
- Es gelten die üblichen Schachregeln, auch Rochade und Schlagen im Vorbeigehen. Ein Bauer auf der letzten Reihe
  wird immer zur Dame.
- Über dem Brett steht, wer dran ist: **Weiß am Zug** oder **Schwarz am Zug**. Während der Gegner überlegt, steht
  dort **Computer überlegt…**.
- Die Partie endet mit Schachmatt (**♔ Weiß gewinnt — Schachmatt!** bzw. **♚ Schwarz gewinnt — Schachmatt!**) oder
  mit **Patt — Remis.**
- **Neue Partie** stellt die Figuren neu auf, der Modus bleibt. **Modus** führt zurück zur Modus-Auswahl.

### Gegen ein KI-Modell
- Unter dem Brett steht der Name des gewählten Modells.
- Das Modell darf nur aus den erlaubten Zügen wählen, die das Spiel ihm schickt. Es kann also keinen falschen Zug
  machen.
- Antwortet das Modell nicht brauchbar oder gibt es einen Fehler, zieht stattdessen der eingebaute Computer. Unter
  dem Brett steht dann **Notzug (Minimax)**. Die Partie läuft einfach weiter.

### Bestenliste
- Rechts neben dem Brett steht die **Bestenliste**. Sie zeigt die Spieler mit den meisten Siegen, höchstens zehn.
- Gespeichert werden beendete Partien gegen den Computer und gegen ein KI-Modell. Partien zu zweit an einem Gerät
  zählen nicht.
- Solange niemand gewonnen hat, steht dort **Noch keine Siege — gewinn gegen den Computer!**

### Fenster schließen
Das Spielfenster schließt du mit dem X oben rechts oder mit der Esc-Taste. Eine laufende Partie geht dabei
verloren.

## Gut zu wissen
- Die Spiel-Logik läuft in deinem Browser. Der Server speichert nur die Ergebnisse beendeter Partien und reicht
  die Züge an das KI-Modell weiter. Der Zugang zum Modell bleibt auf dem Server.
- Brichst du eine Partie ab, wird nichts gespeichert. Ein Ergebnis zählt erst bei Schachmatt oder Patt.
- Die Bestenliste ist für alle Benutzer gleich. Andere sehen dort also deinen Benutzernamen und deine Siege.
- Der eingebaute Computer rechnet drei Züge voraus. Er spielt vernünftig, ist aber kein Profi-Programm.
- Remis gibt es nur durch Patt. Remis durch Zugwiederholung oder die 50-Züge-Regel erkennt das Spiel nicht.
- Beim Spiel gegen ein KI-Modell ist jeder Zug des Modells eine Anfrage an dieses Modell. Bei kostenpflichtigen
  Modellen kostet das Geld. Wie stark das Modell spielt, hängt vom Modell ab.
- Steht dort **Modelle konnten nicht geladen werden.**, ließ sich die Modell-Liste nicht abrufen. Mit **Zurück**
  kannst du dann zu zweit oder gegen den Computer spielen.
- Auf der Buddy-Seite führt bei breitem Fenster der Link **Boardgames** im Kasten **Werkzeuge** ebenfalls hierher.
- Für Brettspiele gibt es keine Agenten-Werkzeuge. Buddy und Agenten können also nicht für dich spielen und deine
  Ergebnisse nicht abrufen.

*Stand: Brettspiele 1.1.1, 22.11.2026*
