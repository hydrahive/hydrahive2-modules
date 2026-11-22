# Game Studio – Spielprojekt anlegen und in deiner Engine öffnen

Das Game Studio macht aus einer Spielidee ein eigenes Projekt mit Workspace. Du beschreibst das Spiel in vier kurzen
Schritten, wählst Godot, Unreal Engine oder Unity und öffnest den Workspace danach über eine Samba-Freigabe in deiner
Engine. Für Unreal legt das Game Studio auf Wunsch gleich ein spielbares Starterprojekt an.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Samba muss auf dem Server laufen. Ob es
   bereit ist, zeigt rechts der Kasten **Samba-Workspace**.
2. Öffne **Game Studio** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Medienstudio**).
3. Wähle unter **Neues Projekt** einen Einstieg: **Neues Spiel**, **Projekt übernehmen** oder **Archiv untersuchen**.
   Neue Projekte kann nur ein Admin anlegen.
4. Schritt **Projekt**: Wähle die **Engine für dieses Projekt**. Bei Unreal trägst du die
   **Unreal-Version für dieses Projekt** ein („auto“ oder eine Nummer wie 5.5). Dann **Arbeitstitel** und
   **Deine Spielidee** ausfüllen und auf **Speichern und weiter** klicken. Erst jetzt wird das Projekt angelegt.
5. Schritt **Details**: **Genre** eintragen und die **Zielplattform** wählen (**Desktop**, **Web** oder **Mobil**).
6. Schritt **Spielinhalt**: Beschreibe bei **Was macht der Spieler?** die wichtigste Aktion und bei
   **Was soll beim Test sichtbar passieren?** das sichtbare Ziel.
7. Schritt **Öffnen**: Bei Unreal klickst du auf **Unreal-Projekt erzeugen**. Danach bindest du die Freigabe ein und
   öffnest den Workspace in deiner Engine.

## Was du damit machen kannst

### Startseite
Oben stehen die drei Einstiege. Alle drei führen durch dieselben vier Schritte und legen ein neues Projekt mit eigenem
Workspace an. Sie unterscheiden sich nur in den Hinweistexten: **Neues Spiel** rät, klein anzufangen,
**Projekt übernehmen** fragt, was schon existiert und nicht überschrieben werden darf, **Archiv untersuchen** fragt
nach Herkunft und Ziel. Vorhandene Dateien kopierst du danach selbst über die Samba-Freigabe in den Workspace.

Unter **Meine Spielprojekte** stehen deine Projekte mit Engine und Fortschritt („Schritt 2 von 4“). Ein Klick öffnet
ein Projekt: Ist die Einrichtung fertig, landest du auf der Arbeitsfläche, sonst im nächsten offenen Schritt.
Daneben zeigt **Samba-Workspace**, ob Samba bereit ist, und den **Freigabe-Benutzer**.

### Die vier Schritte
Oben siehst du die Schritte **Projekt**, **Details**, **Spielinhalt** und **Öffnen**. Fertige Schritte bekommen einen
Haken. Zu einem späteren Schritt kommst du erst, wenn die Pflichtfelder davor ausgefüllt sind. Mit
**Speichern und weiter** wird jeder Schritt gespeichert. Engine und Unreal-Version lassen sich nach dem Anlegen nicht
mehr ändern. Sobald das Projekt existiert, zeigt ein Streifen die Samba-Adresse und den **Freigabe-Benutzer**.
**Zurück zur Übersicht** bringt dich zur Startseite.

### Öffnen in der Engine
- Unreal: **Unreal-Projekt erzeugen** legt im Workspace im Ordner „unreal“ ein C++-Starterprojekt an: die
  `.uproject`-Datei, ein C++-Modul, eine steuerbare Spielfigur, Boden und Ziel. Vorhandene Dateien werden dabei nicht
  überschrieben. Öffne danach die `.uproject`-Datei in Unreal. Beim ersten Öffnen fragt Unreal, ob die Module gebaut
  werden sollen – mit Ja bestätigen.
- Godot und Unity: Hier legt das Game Studio nur den Workspace mit der Freigabe an. Ein Engine-Projekt wird nicht
  automatisch erzeugt.
- **Unter Linux einbinden**: Das Game Studio zeigt einen fertigen Befehl zum Einbinden der Freigabe. Der Knopf mit dem
  Kopier-Zeichen (**Mount-Befehl kopieren**) legt ihn in die Zwischenablage. Du fügst ihn in ein Terminal ein, dort wird das
  Samba-Passwort abgefragt. Der Befehl braucht Administratorrechte auf deinem Rechner (sudo). Darunter steht, welchen
  Ordner du in der Engine öffnest. Alles, was du dort anlegst, landet im Projekt-Workspace.
- Ist die Einrichtung fertig, führt **Zur Projekt-Arbeitsfläche** weiter.

### Projekt-Arbeitsfläche
Oben stehen Titel und Engine. **Einrichtung** öffnet wieder die vier Schritte, **Agent** öffnet den Chat. Darunter gibt
es zwei Reiter:

**Übersicht**
Zeigt **Spielidee**, Kernaktion und sichtbares Ziel sowie **Engine** (bei Unreal mit Version), **Genre** und
**Plattform**. Bei Unreal steht dort auch die **Projektdatei**, außerdem die Samba-Adresse mit dem
**Freigabe-Benutzer**. **Mit dem Agenten weiterplanen** öffnet den Chat mit dem Projektagenten.

**Spieldesign**
Hier liegen deine Planungsdokumente als Markdown. Beim ersten Öffnen legt das Game Studio fünf Vorlagen mit
Leitfragen an: „Spielidee“, „Mechaniken“, „Figuren“, „Welt und Story“ und „Level“. Links wählst du ein Dokument,
rechts schreibst du. Mit Schreibrecht legst du ein neues Dokument an, indem du unten links einen Namen eintippst und auf das
Zeichen daneben (**Dokument anlegen**) klickst oder Enter drückst. **Speichern** (oder Strg+S) sichert die Änderung. Wechselst du mit
ungespeicherten Änderungen das Dokument, fragt das Game Studio vorher nach.

### Chat mit dem Projektagenten
Der Chat öffnet sich rechts neben der Arbeitsfläche. Die Breite ziehst du am linken Rand, das X (**Chat schließen**)
blendet ihn aus. Breite und Zustand merkt sich dein Browser. Du landest jedes Mal wieder in deinem bisherigen Gespräch zu diesem
Projekt.

## Gut zu wissen

- Zugriff: Neue Projekte legt nur ein Admin an. Jedes Spielprojekt ist ein normales HydraHive-Projekt. Ein Admin
  sieht alle Spielprojekte, alle anderen nur die, in denen sie Mitglied sind. Wer nur Leserechte hat, kann Dokumente
  lesen, aber nicht ändern, und keinen Chat starten („Du hast in diesem Projekt nur Leserechte.“).
- Dateien: Alle Angaben liegen als Dateien im Workspace des Projekts, im Ordner „game-studio“: Projektstand,
  Spielbeschreibung, der kleinste spielbare Kern und unter „design“ die Spieldesign-Dokumente. Jedes Projekt bekommt
  eine eigene Samba-Freigabe.
- Gleichzeitiges Bearbeiten: Wurde ein Dokument inzwischen geändert, etwa vom Agenten, wird deine Fassung nicht
  blind überschrieben. Es erscheint „Das Dokument wurde inzwischen geändert (z. B. vom Agenten). Deine Änderung wurde
  nicht gespeichert.“ Mit **Neu laden** holst du den aktuellen Stand.
- Grenzen: Ein Dokument darf höchstens 256 KB groß sein, je Projekt gibt es höchstens 200 Dokumente. Zwei
  Dokumente mit demselben Namen gehen nicht („Ein Dokument mit diesem Namen gibt es schon.“).
- Löschen: Im Game Studio gibt es keinen Knopf zum Löschen von Projekten oder Dokumenten.
- Buddy und Agenten: Das Modul bringt keine eigenen Werkzeuge für Buddy oder Agenten mit. Der Projektagent im Chat
  arbeitet im Workspace des Projekts, in dem auch die Planungsdateien liegen. Hat das Projekt keinen Projektagenten,
  steht dort „Dieses Projekt hat keinen Projektagenten.“
- Typische Fehlermeldungen:
  - „Samba ist noch nicht betriebsbereit. Neue Projekte können erst danach angelegt werden.“ Ein Admin muss Samba
    einrichten oder starten.
  - „Das Projekt konnte nicht gespeichert werden.“ Das kommt zum Beispiel, wenn Samba fehlt, wenn HydraHive für den
    Projektagenten kein KI-Modell findet oder wenn jemand das Projekt gleichzeitig geändert hat.
  - „Das Unreal-Projekt konnte nicht erzeugt werden. Vorhandene Dateien wurden nicht überschrieben.“ Das passiert zum
    Beispiel, wenn im Zielordner schon Dateien mit anderem Inhalt liegen.
  - „Game Studio konnte nicht geladen werden“: Mit **Erneut laden** versuchst du es noch einmal. Es werden nie
    erfundene Beispieldaten angezeigt.

*Stand: Game Studio 0.6.1, 22.11.2026*
