# Vibe – eine kleine Web-App im Chat beschreiben und bauen lassen

Mit Vibe beschreibst du in einfachen Worten, was für eine App du willst. Ein eigener Agent baut sie in einem
abgeschotteten Container, und du siehst das Ergebnis direkt neben dem Chat. Jeder Schritt wird gespeichert, sodass du
jederzeit zu einem früheren Stand zurückkannst. Vibe hilft allen, die eine kleine App ausprobieren wollen, ohne selbst
programmieren zu können.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Auf dem Server muss eine Container-Verwaltung
   (incus) laufen. Fehlt sie, zeigt die Seite „Auf diesem Server fehlt die Container-Verwaltung. Vibe kann hier nicht
   laufen.“
2. Öffne **Vibe** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Arbeiten mit Agenten**).
   Vibe sehen und nutzen nur Admins.
3. Unter **Neues Projekt** gibst du bei **Wie soll es heißen?** einen Namen ein (höchstens 60 Zeichen).
4. Bei **Welches Modell soll bauen?** wählst du ein Modell aus.
5. Klicke auf **Los geht’s**. Das Projekt wird eingerichtet. Das dauert ein bis zwei Minuten, du kannst die Seite offen
   lassen.
6. Steht beim Projekt **Bereit**, klicke auf **Öffnen** und beschreibe im Chat, was gebaut werden soll.

## Was du damit machen kannst

### Neues Projekt
Ein Projekt ist eine App. Du gibst ihr einen Namen und wählst das Modell, das bauen soll. **Los geht’s** lässt sich
erst klicken, wenn ein Name eingetragen und ein nutzbares Modell gewählt ist. Danach richtet Vibe im Hintergrund einen
eigenen Container ein. Während der Einrichtung siehst du, welcher Schritt gerade läuft, zum Beispiel
„Werkzeuge installieren“, „Startvorlage kopieren“, „Speicher für Versionen anlegen“ oder „Vorschau starten“.
Die Startvorlage ist eine kleine Web-App (Vite, React, TypeScript), die der Agent dann nach deinen Wünschen umbaut.

### Projektliste
Jedes Projekt zeigt seinen Zustand:
- **Wird vorbereitet …** und **Wird eingerichtet …**: Die Einrichtung läuft noch.
- **Bereit**: Du kannst das Projekt öffnen.
- **Schläft (wacht beim Öffnen auf)**: Das Projekt wurde länger nicht benutzt. Beim **Öffnen** wird es wieder
  gestartet.
- **Hat nicht geklappt**: Die Einrichtung ist an einem Schritt gescheitert. Die Seite nennt den Schritt und die
  letzte Meldung. Mit **Nochmal versuchen** startest du die Einrichtung neu.

Mit **Löschen** und danach **Ja, löschen** entfernst du ein Projekt samt allen Versionen. **Abbrechen** bricht ab.
Während der Einrichtung lässt sich ein Projekt nicht löschen.

### Sag, was du brauchst
Nach dem **Öffnen** siehst du links den Chat mit dem Agenten. Beschreibe, was die App tun oder wie sie aussehen soll,
zum Beispiel „Eine Seite mit Start, Pause und Tagesliste“. Der Agent ändert die App in kleinen Schritten und antwortet
einfach, ohne Fachwörter. Mit **Zur Liste** kommst du zurück zur Projektliste.

Oben rechts kannst du das Modell für dieses Projekt wechseln. Es gilt ab der nächsten Nachricht („Modell gespeichert –
gilt ab der nächsten Nachricht.“).

### So sieht es aus
Rechts oben siehst du die Vorschau deiner App. Sie lädt automatisch neu, wenn der Agent einen Schritt beendet hat.
Mit dem Knopf **Vorschau neu laden** (Pfeil-Symbol) lädst du sie selbst neu. Solange sie noch startet, steht dort
„Vorschau wird vorbereitet …“.

### Versionen
Rechts unten steht die Liste der gespeicherten Schritte, der neueste oben. Nach jedem Schritt des Agenten speichert
Vibe automatisch eine Version. Ihre Beschriftung ist die erste Zeile der Antwort des Agenten, zum Beispiel
„Hintergrund dunkelblau gemacht“. Die erste Version heißt „Start“.

Gefällt dir etwas nicht, klicke bei einem früheren Eintrag auf **Hierhin zurück**. Vibe stellt diesen Stand als
neue Version wieder her, die Zwischenschritte bleiben in der Liste erhalten. Danach erscheint „Zurückgesetzt.“

## Mit Buddy und Agenten

Vibe gibt Buddy und anderen Agenten keine eigenen Werkzeuge. Gebaut wird nur im Chat auf der Vibe-Seite.

Jedes Vibe-Projekt hat seinen eigenen Vibe-Agenten. Seine Werkzeuge sind fest eingestellt und lassen sich nicht
ändern: Dateien lesen und schreiben, Befehle ausführen, im Web suchen, in der Hilfe nachlesen, sich Notizen merken und
eine Aufgabenliste führen. Alle Befehle und Dateien laufen im Container des Projekts, nicht auf dem Server. Von den
Skills ist nur „vibe-regeln“ eingeschaltet.

Was der Agent nicht kann:
- den Server, das Heimnetz oder private Netze erreichen (das Internet geht, zum Beispiel zum Laden von Bausteinen),
- Befehle mit Administratorrechten ausführen,
- Webseiten mit Zugangsdaten des Servers abrufen.

Die Regeln für deine App (Farben, Technik, Verbote) hält der Agent in der Datei `VIBE.md` im Projekt fest und liest sie
vor jeder Änderung.

## Gut zu wissen

- Nur Admins: Seite und Schnittstellen von Vibe sind nur für Admins freigegeben. Jeder Admin sieht nur seine
  eigenen Projekte.
- Abschirmung: Jedes Projekt läuft in einem eigenen, unprivilegierten Container (Standard: 2 Prozessorkerne,
  2 GB Arbeitsspeicher, 10 GB Platz). Ausgehende Verbindungen zu privaten Netzen sind gesperrt.
- Vorschau: Sie lässt sich nur aus privaten Netzen wie dem Heimnetz öffnen. Geöffnet wird sie über ein
  Einmal-Ticket, das 60 Sekunden gilt. Die Anmeldung an der Vorschau gilt danach 8 Stunden und nur für die Vorschau.
- Ruhezustand: Nach 30 Minuten ohne Nutzung wird der Container angehalten, solange der Agent nicht gerade arbeitet.
  Beim Öffnen wacht er wieder auf. Klappt das nicht, steht dort „Das Projekt ließ sich nicht aufwecken. Versuch es
  gleich noch einmal.“
- Modelle: Hat das Agenten-Template „Modul-Schnell“ (unter LLM → Agenten-Templates) eine nutzbare Modellkette, sind
  nur deren Modelle wählbar, sonst alle eingerichteten Chat-Modelle.
  Ist kein Modell eingerichtet, steht im Auswahlfeld „Kein Modell eingerichtet“ und du kannst kein Projekt anlegen.
  Ist das Standardmodell auf dem Server nicht nutzbar, fordert die Seite dich auf, ein anderes zu wählen.
  Bei ChatGPT-Modellen zeigt sich erst beim ersten Chat, ob dein Konto sie nutzen darf.
- Versionen: Die Ordner `node_modules` und `dist` sowie Dateien über 2 MB werden nicht in die Versionen
  aufgenommen. Ein Zurückgehen löscht keine Version.
- Projektordner: Die Dateien eines Projekts liegen im Projektordner von HydraHive und werden in den Container
  eingebunden. Lässt sich der Ordner nicht verbinden, meldet die Seite „Der Projektordner ließ sich nicht mit dem
  Arbeitscontainer verbinden.“
- Typische Meldungen:
  - „Es läuft gerade schon etwas.“ – Warte, bis der laufende Vorgang fertig ist.
  - „Das Projekt ist noch nicht bereit.“ – Die Einrichtung läuft noch.
  - „Die Vorschau konnte nicht eingerichtet werden. …“ – Auf dem Server fehlt vermutlich eine Berechtigung für den
    Webserver; ein Admin muss das prüfen.
  - „Der Arbeitscontainer ließ sich nicht sicher entfernen. …“ – Das Projekt bleibt erhalten; versuche das Löschen
    erneut.
- Kosten: Jede Nachricht im Chat startet einen Lauf des gewählten Sprachmodells. Je nach Modell und Anbieter kostet
  das Geld.

*Stand: Vibe 0.2.2, 22.11.2026*
