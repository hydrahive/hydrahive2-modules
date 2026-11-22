# Video-Editor – Videos im Browser schneiden, vertonen und exportieren

Der Video-Editor ist ein Schnittplatz direkt im Browser. Du nimmst ein Video aus deinem Projekt, schneidest die
guten Stellen heraus, legst Musik oder Ton darunter und exportierst das Ergebnis als neue MP4-Datei. Das Original
bleibt dabei unverändert.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Der Editor arbeitet immer in einem Projekt. Erscheint „Keine Projekte vorhanden. Lege zuerst ein Projekt an.“,
   lege zuerst unter **Projekte** eines an.
3. Öffne den **Video-Editor** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Medienstudio**).
4. Wähle oben neben der Überschrift das Projekt aus.
5. Klicke **Aus Projekt hinzufügen** oder **Video hochladen**. Sobald das Video aufbereitet ist, erscheint es als
   Kachel. Ein Klick darauf öffnet den Schnitt.

## Was du damit machen kannst

### Bibliothek
- Die Startseite zeigt alle Videos, die du schon für den Schnitt aufbereitet hast. Jede Kachel nennt Auflösung,
  Dateiname, Ort im Projekt, Länge und die Zahl der Clips.
- **Aus Projekt hinzufügen** öffnet das Fenster **Videos im Projekt**. Es listet alle Videos, die irgendwo im
  Projekt liegen, zum Beispiel Clips aus dem Atelier. **Hinzufügen** bereitet ein Video auf, ohne es zu kopieren.
  Schon aufbereitete Videos tragen den Hinweis „bereits hinzugefügt“.
- **Video hochladen** lädt ein Video von deinem Rechner ins Projekt. Erlaubt sind MP4, MOV, MKV, WebM und AVI bis
  4 GB pro Datei.
- Beim Aufbereiten entsteht eine kleinere Vorschaufassung, damit das Vorspulen flüssig läuft, dazu ein Filmstreifen
  mit Vorschaubildern. Während das läuft, steht am Knopf „Bereitet auf…“ bzw. „Lädt hoch…“.

### Schnitt
- Oben stehen Name, Auflösung, Bildrate und Länge des Videos. **← Bibliothek** führt zurück. Rechts zeigt
  „gespeichert“, dass dein Schnitt gesichert ist. Jede Änderung wird kurz danach von selbst gespeichert.
- Darunter läuft die Vorschau. Ein Klick ins Bild startet oder stoppt sie.
- Die Timeline zeigt eine Zeitleiste, die Keyframes (Schlüsselbilder) und einen Filmstreifen. Klicken oder
  Ziehen setzt die Abspielposition. Das Mausrad scrollt, mit gedrückter Strg-Taste (Mac: Cmd) zoomt es.
- Ein Clip ist ein Ausschnitt aus dem Video. So legst du einen an:
  - **In (I)** merkt sich den Anfang an der aktuellen Position, **Out (O)** setzt das Ende und legt den Clip an.
  - **Split (S)** teilt den Clip an der Abspielposition in zwei.
  - **Löschen** entfernt den ausgewählten Clip.
  - Die Ränder eines ausgewählten Clips kannst du mit der Maus ziehen, um ihn kürzer oder länger zu machen.
- Die Clips stehen immer in der Reihenfolge, in der sie im Original vorkommen. Umsortieren geht nicht.
- **↩︎** und **↪︎** machen Schritte rückgängig oder wiederholen sie.
- **⇤kf** und **kf⇥** springen zum vorigen bzw. nächsten Keyframe, **◀|** und **|▶** gehen ein Bild zurück oder vor.
- **▶ Clip** spielt den ausgewählten Clip, **▶▶ Schnitt** spielt alle Clips hintereinander ab, ohne etwas zu
  rendern. **■ Stop** hält an.

### Keyframes und verlustfreies Schneiden
- **🧲 Snap** (an/aus) lässt Schnitte auf Keyframes einrasten. Daneben steht „● auf Keyframe“ oder „○ zwischen
  Keyframes“.
- Liegen beide Ränder eines Clips auf Keyframes, wird er beim Export einfach kopiert: schnell und ohne
  Qualitätsverlust. Sonst wird er neu berechnet und bildgenau geschnitten.
- Am ausgewählten Clip zeigt ein Knopf den Modus, **⚡ Kopieren** oder **⟳ Neu kodieren**. Ein Klick schaltet um.
  Kopiert wird beim Export trotzdem nur, wenn der Clip-Anfang auf einem Keyframe liegt.

### Ton
- **Audio hinzufügen** öffnet die **Audio-Bibliothek** mit allen Audiodateien im Projekt (MP3, WAV, M4A, OGG,
  FLAC, AAC), zum Beispiel Musik aus dem Atelier. **Aufbereiten** bereitet eine Datei vor, **Einfügen** setzt sie an
  der Abspielposition auf die unterste Audiospur. Gibt es noch keine Spur, wird eine angelegt.
- Unter der Timeline liegen die Spuren. Die erste Zeile ist der **Original-Ton** des Videos: **M** schaltet ihn
  stumm, der Regler ändert die Lautstärke.
- **+ Audiospur** legt eine weitere Spur an. Je Spur gibt es **M** (stumm), **S** (solo), einen Lautstärkeregler
  und ✕ zum Löschen. Ein Doppelklick auf den Namen benennt die Spur um.
- Audio-Clips kannst du mit der Maus verschieben und an den Rändern kürzen. Ein Klick wählt einen Clip aus. Darunter
  erscheinen dann **Gain** (Lautstärke), **Fade-In** und **Fade-Out** in Sekunden sowie **Split am Playhead** und
  **Löschen**.
- Ist eine Spur auf solo geschaltet, kommen nur die Solo-Spuren in den Export, der Original-Ton dann nicht.

### Exportieren
- **Exportieren** ist aktiv, sobald es mindestens einen Clip gibt. Im Fenster wählst du eine Vorgabe:
  - **Nur schneiden**: Quelle unverändert, sekundenschnell.
  - **YouTube 1080p**: 1080p H.264, 8 Mbit/s.
  - **Web kompakt**: 720p, klein, lädt schnell.
  - **Archiv**: volle Auflösung, HEVC, sehr hohe Qualität.
- **Rendern** speichert zuerst deinen Schnitt und startet dann den Export. Der Fortschritt steht in Prozent dabei.
- Die fertige Datei liegt im Projekt im Ordner `videoeditor/exports/`. Ändert eine Vorgabe Auflösung, Codec oder
  Qualität, werden alle Clips neu berechnet, auch die auf Keyframes.

## Gut zu wissen

- Pro Schnitt bearbeitest du ein einzelnes Video. Mehrere verschiedene Videos zu einem Film zusammensetzen geht
  hier nicht. Dafür gibt es im Atelier den Reiter **Filme**.
- Die Audiospuren hörst du in der Vorschau nicht. Sie werden erst beim Export eingemischt.
- Alles bleibt im Projekt: Hochgeladene Videos landen unter `videoeditor/uploads/`, Vorschaufassungen und Exporte
  ebenfalls im Ordner `videoeditor/`. Projektvideos werden nicht kopiert.
- Andere Nutzer sehen deine Videos nur, wenn sie Zugriff auf das Projekt haben.
- Der Editor rechnet auf dem eigenen Server. Es entstehen keine Kosten bei einem KI-Anbieter.
- Im Atelier ist der Video-Editor als Reiter **Schnitt** eingebaut. Er funktioniert dort genauso. Das Atelier
  braucht deshalb dieses Modul.
- Tastenkürzel: Leertaste spielt ab oder hält an, ← und → gehen ein Bild weiter (mit Umschalt zehn Bilder),
  J und L springen 10 Sekunden zurück oder vor, [ und ] springen zum vorigen bzw. nächsten Keyframe, Entf löscht den
  ausgewählten Clip, Strg+Z macht rückgängig, Strg+Umschalt+Z oder Strg+Y wiederholt.
- Typische Meldungen:
  - „Noch keine Videos. Füge eins aus dem Projekt hinzu oder lade eins hoch!“: Die Bibliothek ist leer.
  - „Keine Videos im Projekt-Workspace gefunden.“: Im Projekt liegt noch kein Video. Lade eins hoch oder erzeuge
    eins, etwa im Atelier.
  - „Keine Audioquellen im Projekt.“: Im Projekt liegt keine Audiodatei.
  - „Upload fehlgeschlagen“, „Import fehlgeschlagen“ oder „Export fehlgeschlagen“: Der Grund steht in roter Schrift
    darunter. Beim Export führt **Zurück** wieder zur Auswahl der Vorgabe.

*Stand: Video-Editor 0.2.3, 22.11.2026*
