# Radiostream – dein eigenes Webradio aus der Musik auf dem NAS

Radiostream macht aus deiner Musiksammlung auf dem NAS einen eigenen Radiosender. Das Modul liest die Sammlung
ein, spielt daraus rund um die Uhr ein Programm und stellt eine eigene Seite zum Zuhören bereit, für die niemand
ein HydraHive-Konto braucht. Es hilft allen, die ihre Musik zu Hause und unterwegs als Radio hören wollen.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Dabei werden die Sendeprogramme
   Liquidsoap und Icecast sowie ffmpeg eingerichtet. Der Sender startet dabei nicht von selbst.
2. Unter **Credentials** legt der Admin einen Zugang vom Typ **Basic Auth (user:pass)** mit Benutzer und
   Passwort für die Musik-Freigabe an.
3. **Radiostream** öffnen (Gruppe **Arbeiten**) und den Reiter **Quelle** wählen. Bei **Adresse der Freigabe**
   die Adresse eintragen, sie beginnt mit `smb://`, zum Beispiel `smb://server/freigabe`. Bei
   **Zugang aus dem Safe** den eben angelegten Zugang wählen.
4. **Verbindung prüfen** klicken. Klappt es, steht dort „Verbunden – … Ordner gefunden.“ Dann **Jetzt einlesen**
   klicken. Das speichert die Quelle und liest die Bibliothek im Hintergrund ein. Du kannst die Seite dabei
   verlassen.
5. Im Reiter **Sender** auf **Sender starten** klicken. Über **Hörer-Seite öffnen** kommst du zum Player.

## Was du damit machen kannst

Oben auf der Seite stehen die Reiter **Bibliothek**, **Programm** und **Sender**. Admins sehen zusätzlich
**Quelle**.

### Bibliothek
- Oben stehen die Zahlen zur Sammlung: wie viele **Titel** und **Künstler** es gibt und wie lange die Musik
  insgesamt läuft. Fehlen Dateien auf dem NAS oder sind sie nicht lesbar, steht das dort ebenfalls.
- Darunter siehst du den Stand des Einlesens, zum Beispiel „Wird eingelesen: … %“ mit der Restzeit. Admins
  können hier **Bibliothek einlesen** starten oder mit **Abbrechen** stoppen. Wird ein Einlesen unterbrochen,
  bleibt alles erhalten, was schon da ist.
- Im Suchfeld suchst du nach Künstler, Titel oder Album. Filtern kannst du nach **Alle Genres**,
  **Alle Jahrzehnte** (1950er bis 2020er) und **Alle Formate** (MP3 oder FLAC). Mit **Nicht mehr da** siehst du
  Titel, die auf dem NAS verschwunden sind.
- Mit dem Abspielknopf vor jeder Zeile hörst du einen Titel im Browser vor (**Vorhören**, **Anhalten**).
  Weitere Titel holst du mit **Mehr laden**.
- Mit dem Recht „Moderieren“ hat jede Zeile den Knopf **Mehr**: **Als Nächstes spielen**,
  **Ans Ende der Warteschlange** oder **Zu Playlist**. Hast du gesucht oder gefiltert, kannst du mit
  **Alle Treffer hinzufügen** alle Treffer auf einmal in eine Playlist legen.

### Programm
Hier legst du fest, was laufen kann. Links stehen deine Playlisten und Mixe, rechts der gewählte Eintrag.

- **Neue Playlist**: Namen eintippen und **Anlegen**. Danach füllst du sie aus der Bibliothek. Für jede
  Playlist wählst du **Der Reihe nach** oder **Gemischt** und für das Ende **Am Ende von vorn** oder
  **Am Ende zurück zu „Alles“**. Titel sortierst du mit **Nach oben** und **Nach unten** um oder nimmst sie mit
  **Entfernen** heraus. Am Rechner geht das Umsortieren auch per Ziehen. **Playlist löschen** fragt vorher nach. Die Musik selbst bleibt in der Bibliothek.
- **Neuer Mix**: Ein Mix ist eine Regel statt einer festen Liste. Du wählst **Genres**, **Interpreten**,
  **Jahrzehnte** und **Ordner**. Unter **Ausschließen** nimmst du Genres, Interpreten oder Ordner wieder heraus.
  Mit **Auch sehr lange Titel (über 15 Minuten)** dürfen auch lange Stücke hinein. Das Modul zeigt sofort, wie
  viele Titel passen, und nennt ein paar Beispiele. Bei sehr wenigen Titeln warnt es, dass sie sich schnell
  wiederholen. Mit **Speichern** sicherst du den Mix, **Mix löschen** entfernt ihn.
- **Jetzt spielen** schaltet den Sender auf diese Playlist oder diesen Mix um. Umgeschaltet wird nach dem
  laufenden Titel.

Ohne das Recht „Moderieren“ kannst du Playlisten und Mixe nur ansehen.

### Sender
- Oben siehst du, ob der Sender **Auf Sendung** ist oder **Sender ist aus**, welcher Titel gerade läuft und wie
  viele gerade zuhören. Die Anzeige erneuert sich alle 15 Sekunden.
- Mit dem Recht „Sender steuern“ gibt es **Sender starten**, **Sender stoppen** und **Titel überspringen**.
- **Zuletzt gespielt** listet die letzten Titel.
- **Programm** zeigt, was gerade läuft: **Alles** (zufällig aus der ganzen Bibliothek), eine Playlist oder einen
  Mix. Mit dem Recht „Moderieren“ wählst du unter **Was soll laufen?** um.
- **Als Nächstes** ist die Warteschlange. Titel hier laufen vor dem Programm. Mit „Moderieren“ sortierst du sie
  um oder entfernst sie.
- **Einstellungen** (mit „Sender steuern“): **Name des Senders**, **Untertitel**,
  **Gleicher Künstler frühestens nach (Minuten)**, **Gleicher Titel frühestens nach (Tagen)**,
  **Port der Hörer-Seite**, **Höchstens gleichzeitig zuhören** und **Wer darf zuhören?**. Gespeichert wird mit
  **Einstellungen speichern**. Läuft der Sender, startet er dabei kurz neu.
- **Ausgeschlossen von „Alles“** (mit „Sender steuern“): Genres, Wortteile von Genres und Ordner, die nie
  zufällig laufen sollen, etwa Hörbücher. Das Modul schlägt dafür Ordner vor, die überwiegend Hörbücher
  enthalten. In Playlisten und Mixen kannst du diese Titel trotzdem spielen.

### Quelle (nur Admins)
Unter **Musikquelle** trägst du die **Adresse der Freigabe** ein und wählst den **Zugang aus dem Safe**. Ein
Passwort tippst du hier nie ein, es kommt aus dem Safe. Die Knöpfe sind **Verbindung prüfen**, **Speichern** und
**Jetzt einlesen**. Danach liest das Radio jede Nacht um 4 Uhr neue und geänderte Titel nach.

### Hörer-Seite
Die Hörer-Seite ist eine schlichte Seite mit Sendername, Abspielknopf, Lautstärke, „Jetzt läuft“ und
„Zuletzt gespielt“. Über „In VLC oder iTunes öffnen“ hörst du den Sender auch in einem anderen Player. Die
Seite läuft auf einem eigenen Port und braucht keine Anmeldung.

## Gut zu wissen

- Rechte: Nach der Installation dürfen nur Admins das Modul nutzen. Es gibt drei Rechte, die ein Admin
  unter **Freigaben** vergibt: „Radiostream nutzen“, „Sender steuern (starten, stoppen, Einstellungen)“ und
  „Moderieren (Programm, Playlisten, Mixe, Warteschlange)“. Die Musikquelle richtet immer ein Admin ein.
- Nur lesen: Die Musik bleibt auf dem NAS und wird nur gelesen. Dort wird nichts verändert.
- Abwechslung: Voreingestellt kommt derselbe Künstler frühestens nach 60 Minuten wieder, derselbe Titel
  frühestens nach 3 Tagen. Das gilt für **Alles** und für Mixe, nicht für Playlisten und die Warteschlange.
  Gibt ein Mix zu wenig her, lockert das Modul die Sperren, statt zu schweigen.
- Nie Stille: Ist im gewählten Programm gerade kein Titel spielbar, läuft solange **Alles**. Kommt gar kein
  Titel an, etwa weil das NAS weg ist, spielt eine leise Pausenmelodie.
- Klang: Die Titel werden weich überblendet und jeder Titel wird auf eine gleiche Lautheit gebracht. Der
  Stream ist MP3 mit 192 kbit/s.
- Lange Titel: Titel über 15 Minuten laufen in **Alles** und in Mixen nur, wenn du das erlaubst.
- Wer darf zuhören: **Alle (auch aus dem Internet)**, **Nur Heimnetz und Tailscale** oder
  **Niemand – Hörer-Seite aus**. Voreingestellt sind alle, Port 8800 und höchstens 50 Hörer gleichzeitig.
  Damit man von unterwegs zuhören kann, gibst du den Port im Router selbst frei. Das macht HydraHive nicht.
- Abgeschottet: Die Hörer-Seite kennt nur den Player, den Stream und „Jetzt läuft“. Von dort führt kein Weg
  zu HydraHive. Von einer Adresse aus sind höchstens 3 Verbindungen gleichzeitig möglich.
- Grenzen: Eine Playlist fasst bis zu 2000 Titel, auf einmal kommen höchstens 500 dazu. Die Warteschlange
  fasst 100 Titel. Namen dürfen höchstens 80 Zeichen lang sein.
- Kein Buddy: Radiostream hat keine Werkzeuge für Buddy oder Agenten. Bedient wird es nur über die Seite.
- Typische Meldungen:
  - „Der Sender ist auf diesem Server noch nicht eingerichtet. Bitte das Modul einmal aktualisieren.“: Die
    Sendeprogramme fehlen. Ein Admin aktualisiert das Modul.
  - „Die Freigabe lehnt die Anmeldung ab – Benutzer oder Passwort im Safe prüfen.“: Der Zugang im Safe stimmt
    nicht.
  - „Der Server mit der Musik ist nicht erreichbar.“: Das NAS ist aus oder nicht im Netz.
  - „Dieser Port ist auf dem Server schon belegt. Bitte einen anderen wählen.“: Bei **Port der Hörer-Seite**
    einen anderen Port wählen. Erlaubt sind 1024 bis 65535.
  - „Dafür brauchst du das Recht „Moderieren“.“: Ein Admin muss dir das Recht freigeben.

*Stand: Radiostream 0.3.2, 22.11.2026*
