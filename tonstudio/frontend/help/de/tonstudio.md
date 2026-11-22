# Tonstudio – Musik-Clips mit KI erzeugen und sammeln

Im Tonstudio lässt du kurze Musikstücke und ganze Songs von einer KI erzeugen, lädst eigene Audiodateien hoch und
hörst alles in einer Bibliothek an. Alles gehört zu einem Projekt. Es hilft allen, die für ein Projekt Musik
brauchen, etwa für einen Film, ein Hörspiel oder einfach zum Ausprobieren.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Für das Erzeugen braucht HydraHive einen OpenRouter-Schlüssel. Ohne ihn meldet das Tonstudio
   „Kein OpenRouter-Schlüssel eingerichtet (Einstellungen → KI-Modelle).“
3. Öffne das **Tonstudio** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Medienstudio**).
4. Wähle links oben unter **Projekt** dein Projekt. Hast du noch keins, lege zuerst unter **Projekte** eines an.
5. Schreib rechts unter **Clip erzeugen** einen Stil oder eine Beschreibung und klicke auf **Erzeugen**.
   Ist der Clip fertig, steht dort „Fertig: …“ und er erscheint in der **Bibliothek**.

## Was du damit machen kannst

Die Seite hat drei Spalten: links **Projekt** und **Songs**, in der Mitte die **Bibliothek**, rechts
**Clip erzeugen**.

### Songs
- Gib einen Namen in das Feld „Titel des Songs“ ein und klicke auf **Neuer Song**.
- In der Liste steht zu jedem Song die Zahl der Spuren und, falls gesetzt, Tempo (BPM) und Tonart.
- Mit dem Stift (**Umbenennen**) gibst du einem Song einen neuen Titel.
- Mit dem Mülleimer (**In den Papierkorb**) legst du einen Song nach einer Rückfrage in den Papierkorb.
  Gibt es dort Songs, erscheint unter der Liste „Papierkorb (Anzahl)“. Ein Klick klappt ihn auf, mit
  **Wiederherstellen** holst du einen Song zurück.
- Das Tonstudio ist in seiner ersten Etappe: Songs lassen sich anlegen und verwalten, eine Zeitachse zum
  Anordnen und Mischen gibt es hier noch nicht. Das steht auch als Hinweis unter der Projektauswahl.

### Bibliothek
- Hier liegen alle Audiodateien des Projekts als kleine Kacheln, gegliedert nach Herkunft:
  - **Tonstudio-Clips**: was du im Tonstudio erzeugt oder hochgeladen hast.
  - **Atelier**: Ton aus dem Atelier.
  - **Von Agenten erzeugt**: Musik, die Agenten im Projekt erzeugt haben.
  - **Medien (Musicplayer)**: Musik aus dem Medienordner des Projekts.
- Ein kleines Zeichen vor dem Namen zeigt die Herkunft: ✨ **Erzeugt**, ⬆️ **Hochgeladen**,
  📁 **Aus dem Projekt**.
- Jede Kachel zeigt Name, Länge, Modell und Datum. Erzeugte Clips heißen nach der ersten Zeile deiner
  Beschreibung bzw. deines Stils. Dateien ohne bekannten Namen erscheinen kursiv als „Song vom …“ mit Datum und Uhrzeit.
- Mit ▶ (**Abspielen**) hörst du einen Clip, mit ❚❚ (**Pause**) hältst du an. Es spielt immer nur ein Clip.
  Ein Klick in den schmalen Balken unter dem Namen springt an diese Stelle.
- Oben suchst du mit „Suchen (Name, Prompt, Modell)“ und sortierst nach **Neueste zuerst**, **Name A–Z**
  oder **Längste zuerst**.
- **Hochladen** fügt eine eigene Audiodatei hinzu. Erlaubt sind MP3, WAV, FLAC, OGG, M4A, AAC und Opus bis
  100 MB je Datei.
- Fährst du mit der Maus über eine Kachel, erscheinen der Stift und der Mülleimer. Der Stift gibt der Datei einen
  eigenen Anzeigenamen. Lässt du das Feld leer, gilt wieder der ursprüngliche Name. Die Datei selbst bleibt dabei
  unverändert.
- Der Mülleimer (**Clip löschen**) entfernt nach einer Rückfrage einen Tonstudio-Clip. Bei Dateien aus Atelier,
  Agenten-Ordner oder Medien gibt es keinen Mülleimer. Sie bleiben immer unberührt.
- Liegt dieselbe Datei mehrfach im Projekt, zeigt die Bibliothek sie nur einmal, mit dem Hinweis
  „+1 Kopie“ bzw. „+… Kopien“.

### Clip erzeugen
- Oben wählst du das Musik-Modell. In der Liste stehen die Musik-Modelle, die OpenRouter gerade anbietet,
  zum Beispiel Lyria von Google. Laut Modul-Angaben liefert die Pro-Variante ganze Stücke von etwa 2:30 bis
  3:00 Minuten, die Clip-Variante immer etwa 30 Sekunden.
- Unter dem Modell steht, was es kann, zum Beispiel „eigener Liedtext“ oder „Bild-Referenz“, und ein Hinweis zu
  den Kosten. Eine Bild- oder Audio-Referenz kannst du im Tonstudio selbst nicht mitgeben.
- Fülle aus, was du möchtest: Stil (zum Beispiel Epic Orchestral, Folk Rock), Beschreibung (Stimmung,
  Instrumente, Aufbau), BPM, Tonart und Länge in Sekunden.
- **Instrumental (ohne Gesang)** bestellt Musik ohne Stimme. Ist das Häkchen aus und kann das Modell eigenen
  Text singen, erscheint ein Feld „Liedtext (optional)“.
- **Erzeugen** startet den Auftrag. Der Knopf bleibt grau, solange weder Stil noch Beschreibung noch Liedtext
  eingetragen ist. Während der Arbeit steht dort **Wird erzeugt…**.

## Gut zu wissen

- Rechte: Nach der Installation dürfen nur Admins das Tonstudio nutzen. Ein Admin kann das Recht
  „Tonstudio nutzen“ unter **Freigaben** an andere vergeben. Auf Songs und Dateien eines Projekts haben nur dessen
  Mitglieder Zugriff.
- Datenschutz: Zum Erzeugen gehen Stil, Beschreibung, Tempo, Tonart, Länge und Liedtext an OpenRouter und von dort
  an den Anbieter des Modells. Hochgeladene Dateien bleiben im Projekt.
- Kosten: Das Tonstudio zeigt „Kosten unbekannt – OpenRouter meldet 0“. Was ein Clip kostet, siehst du bei
  OpenRouter selbst.
- Wünsche, keine Garantie: BPM, Tonart und Länge gehen nur als Wunsch an das Modell. Ob es sie genau trifft,
  ist nicht sicher. Das steht auch im Formular.
- Kommt vom Modell ohne erkennbaren Grund kein Ton zurück, fragt das Tonstudio einmal von selbst neu an. Klappt
  es dann noch nicht, steht dort „Keine Audio-Daten erhalten – bitte noch einmal versuchen.“
- Ein Clip wird nur gespeichert, wenn er wirklich lesbares Audio enthält. Das gilt auch für Uploads, sonst kommt
  „Upload abgelehnt: Die Datei enthält kein lesbares Audio“.
- Songs im Papierkorb lassen sich wiederherstellen. Ein gelöschter Clip ist dagegen weg.
- „Der Song wurde inzwischen woanders geändert … Bitte neu laden.“ heißt: Jemand hat den Song gleichzeitig
  geändert. Lade die Seite neu und versuche es dann noch einmal.
- Das Modul **Studio** beschreibt sich selbst als Nachfolger: Es „löst Atelier, Video-Editor und Tonstudio ab“.
  Clips aus dem Tonstudio erscheinen dort automatisch in der Bibliothek und lassen sich in Filme einbauen.

*Stand: Tonstudio 0.3.2, 22.11.2026*
