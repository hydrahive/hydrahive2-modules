# Mediaplayer – Musik und Videos eines Projekts direkt in HydraHive abspielen

Der Mediaplayer spielt Audio und Video direkt in der App ab: eigene Dateien, im Atelier erzeugte Musik, Szenen-Clips
und Filme sowie Medien, die ein Agent erzeugt hat. Jedes Projekt hat seine eigene Sammlung. Du schaltest zwischen
**Audio** und **Video** um, die Musik läuft dabei weiter.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Wähle bei Buddy ein Projekt. Der Mediaplayer zeigt immer die Medien dieses Projekts. Ohne Projekt steht dort
   **Projekt wählen**.
3. Öffne **Mediaplayer** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Medienstudio**).
   Den Player gibt es auch als Kasten auf der Buddy-Seite.
4. Lade mit **Audio hochladen** eine Datei hoch oder hol unter **Aus dem Projekt** ein vorhandenes Stück in den
   Player. Ein Klick auf den Eintrag in der Liste spielt ihn ab.

## Was du damit machen kannst

### Audio und Video umschalten
- Oben wählst du **Audio** oder **Video**. Der Player merkt sich die Wahl je Projekt in deinem Browser.
- Läuft Musik und du wechselst zu **Video**, spielt die Musik weiter.

### Audio
- Unter **Aktuelle Wiedergabe** steht der laufende Titel, sonst **Nichts ausgewählt**. Kleine bunte Balken
  bewegen sich, solange Musik läuft.
- Mit dem Schieber springst du an eine Stelle im Titel. Links und rechts stehen die abgelaufene Zeit und die
  Gesamtlänge.
- Die Knöpfe: **Zufallswiedergabe**, **Vorheriger**, **Abspielen** bzw. **Pause**, **Nächster** und
  **Wiederholen**. **Wiederholen** schaltet bei jedem Klick weiter: erst die ganze Liste wiederholen, dann
  **Titel wiederholen** (ein Lied in Schleife), dann wieder aus.
- Ohne Wiederholen stoppt die Wiedergabe nach dem letzten Titel der Liste.
- Darunter regelst du mit dem zweiten Schieber die Lautstärke.
- Die Liste darunter zeigt alle Audio-Titel des Projekts, die neuesten oben. Bei erzeugten Stücken steht unter dem
  Titel, wenn vorhanden, die Beschreibung (Prompt), das Modell und die Dauer.

### Video
- Ein Klick auf ein Video in der **Playlist** startet es im großen Bild. Darunter steht der Titel.
- Mit **Vollbild** füllt das Video den ganzen Bildschirm.
- Im Kasten auf der Buddy-Seite gibt es zusätzlich **Groß öffnen**. Das öffnet die Seite **Mediaplayer**.
- Läuft gerade Musik, steht oben eine schmale Leiste mit dem Titel. Dort pausierst du die Musik oder setzt sie fort.
  Ein Klick auf den Titel wechselt zurück zu **Audio**.
- Es spielt immer nur eins mit Ton: Startest du ein Video, pausiert die Musik. Hältst du das Video an oder ist es zu
  Ende, läuft die Musik weiter, wenn sie vorher lief.
- Kann dein Browser ein Video nicht abspielen, erscheint **Dein Browser unterstützt dieses Video nicht.**

### Hochladen
- Mit **Audio hochladen** bzw. **Video hochladen** wählst du eine Datei von deinem Rechner. Während des Hochladens
  steht dort **Lädt hoch…**.
- Erlaubt sind für Audio MP3, WAV, OGG, M4A und FLAC (höchstens 50 MB), für Video MP4 und WebM (höchstens 60 MB).
- Als Titel nimmt der Player den Dateinamen ohne Endung.

### Aus dem Projekt
- **Aus dem Projekt** klappt eine Liste mit Medien auf, die schon im Projekt liegen. Sie ist nach Herkunft
  sortiert: **Agent (generiert)**, **Atelier · Musik**, **Atelier · Szenen-Clips**, **Atelier · Filme** und
  **Hochgeladen (Medienordner)**. Es erscheint nur, was zur gewählten Medienart passt.
- Mit dem Pfeil (**In den Player holen**) kommt ein Stück in den Player. Ein grüner Haken statt des Pfeils zeigt: Das Stück ist schon im Player.
- Von einem Agenten erzeugte Stücke heißen im Player „Generiert · …“ mit ihrem Dateinamen.
- Ist nichts da, steht dort **Nichts gefunden.**

### Herunterladen und Löschen
- Neben jedem Eintrag lädst du die Datei mit dem Pfeil nach unten herunter.
- Der Mülleimer löscht den Eintrag aus dem Player. Ihn sehen nur Projekt-Admins.

## Gut zu wissen
- Wer was darf, richtet sich nach deiner Rolle im Projekt: Alle Mitglieder können abspielen und herunterladen.
  Hochladen und **Aus dem Projekt** gibt es ab Schreibrecht, Löschen nur für Projekt-Admins. Admins von HydraHive
  dürfen alles.
- Ist eine Liste leer, steht dort **Noch keine Medien. Lade welche hoch!**
- Klappt etwas nicht, steht der Grund unter dem Knopf. Typisch beim Hochladen: „Dateiendung nicht unterstützt“,
  „Datei ist leer“ oder „Datei zu groß (max. 50 MB)“ bzw. „(max. 60 MB)“. Beim Holen aus dem Projekt:
  „Track bereits importiert“ oder „Medienquelle nicht gefunden“.
- Lautstärke, Zufall und Wiederholen merkt sich der Player nicht. Nach dem Neuladen der Seite gelten wieder die
  Grundeinstellungen.
- Die bunten Balken neben dem Titel sind nur eine Anzeige. Einen Klangregler (Equalizer) zum Einstellen gibt es nicht.
- Der Mediaplayer hat keine Agenten-Werkzeuge. Buddy und Agenten können ihn nicht steuern. Was ein Agent erzeugt,
  holst du selbst über **Aus dem Projekt** in den Player.

*Stand: Mediaplayer 1.3.4, 22.11.2026*
