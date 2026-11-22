# Diagramme – Agenten zeichnen dir Abläufe und Überblicke

Mit dem Modul Diagramme zeichnen Agenten dir einen Ablauf, den Aufbau eines Systems, eine Datenbank oder eine
Zeitleiste als interaktives Bild. Lange Textlisten werden so zu einem Überblick, den man auf einen Blick versteht.
Jedes Diagramm wird gespeichert und liegt danach in deiner Sammlung.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Dein Buddy kann danach sofort zeichnen. Für Projekt-Agenten und Spezialisten öffnet ein Admin **Diagramme**
   und klickt auf **Für alle Agenten freischalten**.
3. Bitte einen Agenten im Chat, zum Beispiel: „Zeichne mir den Ablauf … als Diagramm.“
4. Das Diagramm erscheint direkt im Chat. Später findest du es unter **Diagramme** in der Navigation
   (Gruppe **Arbeiten**, auf der Startseite im Bereich **Schreibbüro**).

## Was du damit machen kannst

### Diagramme im Chat
Das Diagramm steht als bedienbarer Rahmen in der Unterhaltung. Es lädt erst, wenn du dorthin scrollst.
Mit **Groß öffnen** füllt es den ganzen Bildschirm, mit dem X oben rechts geht es zurück.
Lässt es sich nicht laden, steht dort „Die Ansicht lässt sich gerade nicht laden.“ und du kannst **Neu laden** klicken.

Ein gezeichnetes Diagramm hat eine eigene Bedienleiste. Ihre Beschriftungen sind englisch.
Dort wechselst du zwischen hell und dunkel und speicherst über **Export** ein Bild.
Bei Diagrammen kannst du außerdem vergrößern, verkleinern und die Ansicht zurücksetzen.

### Arten von Diagrammen
Agenten können diese Arten zeichnen. So heißen sie in der Sammlung:
**Ablauf**, **Aufbau**, **Datenfluss**, **Gesprächsfolge**, **Zustände**, **Datenbank**, **Klassen**, **Baum**,
**Zeitleiste**, **Zeitverlauf** und die **Antwort-Seite**. Die Antwort-Seite zeigt das Ergebnis zuerst,
darunter folgen Abschnitte.

### Die Sammlung
Unter **Diagramme** liegen alle Diagramme, die Agenten für dich erstellt haben. Jede Kachel zeigt ein Vorschaubild,
den Titel, die Art, das Projekt und das Datum. Gibt es kein Bild, steht dort **Keine Vorschau**.

- **Nach Titel suchen …**: Das Suchfeld findet Diagramme über ihren Titel.
- **Alle Projekte**: Hier filterst du nach einem Projekt. **Ohne Projekt** zeigt Diagramme, die außerhalb
  eines Projekts entstanden sind.
- **Papierkorb**: Mit diesem Haken siehst du die weggeworfenen Diagramme.

Hast du noch keine Diagramme, steht dort ein Beispiel, wie du einen Agenten fragst.

### Ein Diagramm ansehen
Ein Klick auf eine Kachel öffnet das Diagramm groß. Oben stehen Art, Projekt und Datum.

- **Herunterladen** speichert das Diagramm als Webseite (HTML-Datei). Du kannst sie ohne HydraHive im Browser öffnen.
- **Zurück zur Übersicht** bringt dich zur Sammlung.

### Frühere Fassungen
Ändert ein Agent ein Diagramm, entsteht eine neue Fassung. Die alte bleibt erhalten.
In der Kachel steht dann zum Beispiel „3 Fassungen“. In der Ansicht findest du unter **Frühere Fassungen**
alle Stände mit Datum, die neueste ist mit „(aktuell)“ markiert. Ein Klick zeigt den jeweiligen Stand.

### Papierkorb und Löschen
- **In den Papierkorb** wirft das Diagramm samt allen Fassungen weg.
- Im **Papierkorb** holst du es mit **Wiederherstellen** zurück.
- **Endgültig löschen** geht nur aus dem Papierkorb. Vorher fragt ein Fenster nach.
  Dort bestätigst du mit **Endgültig löschen** oder brichst mit **Abbrechen** ab.
  Das lässt sich nicht rückgängig machen.

### Für alle Agenten (nur Admins)
Admins sehen oben in der Sammlung den Kasten **Für alle Agenten**. Er zeigt, wie viele Agenten Diagramme
erstellen können.

- **Für alle Agenten freischalten** gibt allen aktiven Agenten die Diagramm-Werkzeuge.
  Agenten, die abgeschaltet sind oder die Werkzeuge schon haben, bleiben unverändert.
- **Wieder zurücknehmen** nimmt die Werkzeuge genau bei den Agenten wieder weg, die sie durch diesen Knopf bekommen
  haben. Agenten, die die Werkzeuge vorher schon hatten, behalten sie.

## Mit Buddy und Agenten

Agenten haben drei Werkzeuge:

- **diagramm_hilfe** zeigt dem Agenten die Arten und für jede Art Aufbau und Beispiel.
- **diagramm_erstellen** zeichnet und speichert ein Diagramm. Es erscheint im Chat und in der Sammlung.
  Mit Bezug auf ein vorhandenes Diagramm entsteht eine neue Fassung, die alte bleibt.
  Liegt Code im Projekt, kann der Agent einen Ordner daraus angeben und auf die gelesenen Stellen verweisen.
- **diagramm_liste** zeigt die gespeicherten Diagramme (je Diagramm die neueste Fassung, höchstens 30),
  auf Wunsch nach Titel oder nur aus dem aktuellen Projekt.

Das kannst du zum Beispiel fragen:
- „Mach mir einen Überblick über … als Diagramm.“
- „Zeichne mir die Tabellen dieser Datenbank.“
- „Ändere das Diagramm von gestern: Schritt 3 fehlt.“

Das geht nicht:
- Agenten können Diagramme nicht löschen. Wegwerfen und Löschen geht nur in der Sammlung.
- Agenten sehen und ändern nur Diagramme, die dir gehören oder aus einem deiner Projekte stammen.
  Das gilt auch für Admins.
- Klappt das Zeichnen nicht, bessert der Agent nach. Nach drei Versuchen soll er dir sagen, was nicht klappt.

## Gut zu wissen

- **Sehen dürfen:** du selbst, Admins und Mitglieder des Projekts, in dem das Diagramm entstanden ist.
- **Ändern dürfen:** In den Papierkorb werfen, wiederherstellen und endgültig löschen darf nur, wer das Diagramm
  erstellt hat, oder ein Admin. Projekt-Mitglieder dürfen nur ansehen und herunterladen.
- **Kosten:** Die Diagramme entstehen auf deinem Server mit dem freien Werkzeug Archify, ohne Bezahldienst.
  Nur der Agent verbraucht beim Beschreiben wie gewohnt Tokens.
- **Abgeschottet:** Ein Diagramm ist eine kleine Webseite, die ein Agent gebaut hat. Sie läuft abgeschirmt:
  Sie kann nichts nachladen, nichts senden und kommt nicht an deine Anmeldung.
- **Vorschaubilder** brauchen einen Chromium-Browser auf dem Server. Fehlt er, steht in der Kachel **Keine Vorschau**.
  Das Diagramm selbst funktioniert trotzdem.
- **Grenzen:** Die Beschreibung eines Diagramms darf höchstens 512 KB groß sein. Das Zeichnen bricht nach drei Minuten ab.
- **Typische Meldungen:**
  - „Die Beschreibung ist zu groß.“ – das Diagramm ist zu umfangreich, lieber aufteilen.
  - „Das Erstellen hat zu lange gedauert.“ – der Agent soll es kleiner noch einmal versuchen.
  - „Auf dem Server fehlt ein Programm zum Erstellen.“ – auf dem Server fehlt Node. Das muss ein Admin beheben.
  - „Der Ordner liegt nicht im Projekt.“ – der angegebene Code-Ordner liegt außerhalb des Projekts.
  - „Nur wer das Diagramm erstellt hat, kann es wegwerfen.“ – du siehst das Diagramm, es gehört aber jemand anderem.
  - „Dieses Diagramm gibt es nicht (mehr).“ – es wurde gelöscht oder du darfst es nicht sehen.

*Stand: Diagramme 0.2.4, 22.11.2026*
