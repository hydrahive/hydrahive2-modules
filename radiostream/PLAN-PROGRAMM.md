# Radiostream – Bauplan Etappe „Programm“ (Playlisten, Mixe, Als Nächstes)

> Wunsch Till (31.10.2026): „derzeit ist es nur zufallsgesteuert was gesendet wird und ich habe keinerlei Einfluss
> drauf.“ Playlisten per Suchen und Reinziehen, oder eine Kategorie/einen Interpreten wählen, aus dem der Sender
> zufällig spielt. Kommt vor dem Live-Studio (PLAN-E3.md). Version **0.3.0**.

## Befund (31.10., echte Bibliothek .2, nur gelesen)

- 175.462 Titel. 334 Genres mit mindestens 50 Titeln. Jahr bei 99 % gesetzt.
- Viele Titel haben **mehrere Genres** in einem Feld, z. B. `Pop;Rock`, `Hard Rock;Rock`. Ein Mix „Rock“ muss die
  mitnehmen → Genres werden an `;` geteilt und einzeln verglichen (ohne Groß-/Kleinschreibung).
- **Hörbücher und Hörspiele laufen heute mit:** ~4.200 Titel mit Genre wie „Kids; Audiobooks“, Hörspiel, Spoken Word
  (davon 3.400 Bibi Blocksberg). 463 Titel sind länger als 15 Minuten.

## Was der Admin bekommt

### 1. Programm wählen (Reiter „Sender“, Kasten „Programm“)
- **Alles** (wie heute, aber ohne Hörbücher – siehe Punkt 4), **eine Playlist** oder **ein Mix**.
- Umschalten wirkt ab dem nächsten Titel. Der laufende Titel spielt zu Ende, die Überblendung bleibt.
- Anzeige: „Es läuft: Mix ‚Rock der 80er‘ – 2.431 Titel“ bzw. „Playlist ‚Party‘ – Titel 12 von 40“.

### 2. Playlisten (neuer Reiter „Programm“)
- Anlegen, umbenennen, löschen (eigener Dialog), beliebig viele.
- **Titel hinzufügen:** in der Bibliothek suchen (vorhandene Suche und Filter), dann
  - am Rechner per **Ziehen** auf eine Playlist in der Seitenleiste,
  - überall (auch Handy) per Knopf **„+ Playlist“** an der Titelzeile, dann Playlist wählen.
  - „Alle Treffer hinzufügen“ (höchstens 500 auf einmal).
- **Reihenfolge** per Ziehen ändern (am Handy: Pfeile hoch/runter), Titel entfernen.
- Abspielart je Playlist: **der Reihe nach** oder **gemischt**; am Ende **von vorn** oder **zurück zum Mix/Alles**.
- Sperren für Künstler und Titel gelten bei Playlisten **nicht** (bewusst gewählt). Bei „gemischt“ läuft kein Titel
  zweimal, bevor alle einmal liefen.
- Titel, die nicht mehr in der Bibliothek sind, werden übersprungen und in der Playlist grau angezeigt.

### 3. Mixe (Reiter „Programm“)
- Ein Mix ist eine **Regel**, aus der der Sender zufällig spielt (mit den Sperren für Künstler/Titel wie heute):
  - **Genres** (eines oder mehrere, Auswahl aus der Liste mit Anzahl)
  - **Interpreten** (einer oder mehrere, Suche)
  - **Jahrzehnte / Jahr von–bis**
  - **Ordner** (oberste Ordner der Freigabe, z. B. „Johnny Cash“)
  - **Ausschließen:** Genres, Interpreten, Ordner
- Beim Bearbeiten zeigt die Seite sofort, **wie viele Titel** der Mix hat, und 5 Beispiele.
- Unter 20 Titeln: Hinweis, dass sich Titel schnell wiederholen (die Sperren werden dann gelockert wie heute).
- Beispiele als Vorlage zum Anlegen: „Rock“, „80er“, „Johnny Cash“, „Ohne Hörbücher“ (= Alles minus Hörbücher).

### 4. Hörbücher raus aus „Alles“
- Neue Sender-Einstellung **„Ausgeschlossen von Alles“**: Genres/Ordner, die nie zufällig laufen. Voreinstellung:
  Genres mit *Audiobook*, *Hörbuch*, *Hörspiel*, *Spoken*. Änderbar, abschaltbar.
- Zusätzlich: Titel **länger als 15 Minuten** laufen in „Alles“ und in Mixen nur, wenn eingestellt (Voreinstellung
  aus). In Playlisten laufen sie immer.

### 5. Als Nächstes spielen
- An jeder Titelzeile in der Bibliothek und in Playlisten: **„Als Nächstes“** und **„Ans Ende der Warteschlange“**.
- Warteschlange im Reiter „Sender“: sichtbar, Reihenfolge ändern, entfernen. Sie hat Vorrang vor Playlist/Mix/Alles.
- Liquidsoap fragt schon 3 Titel im Voraus an (`prefetch=3`). Damit „Als Nächstes“ wirklich als nächstes kommt, wird
  die Vorschau auf **1** gesenkt (gemessen werden muss, dass dann zwischen zwei Titeln keine Lücke entsteht – das
  Laden vom NAS + Lautheit messen dauert bis 1,6 s, ein Titel läuft Minuten). Alternativ: Liquidsoap-Warteschlange
  (`request.queue`) vor dem AutoDJ über die Steuerdatei. Entscheidung nach Messung auf hydratest.

## Technik

### Daten (Migration `004_program.sql`, additiv)
- `module_radiostream_playlists`: id, name, order_mode (`ordered`|`shuffle`), at_end (`repeat`|`back`), created_at/by,
  updated_at.
- `module_radiostream_playlist_items`: playlist_id, pos, track_id (Lücken erlaubt, Umsortieren schreibt pos neu).
- `module_radiostream_mixes`: id, name, rules (JSON: genres, artists, decades, year_from/to, folders, exclude_*),
  allow_long, created_at/by, updated_at.
- `module_radiostream_queue`: id, pos, track_id, added_by, added_at.
- `module_radiostream_program`: eine Zeile – mode (`all`|`playlist`|`mix`), ref_id, playlist_cursor, shuffle_seed,
  shuffle_played (JSON der schon gespielten bei „gemischt“).
- `module_radiostream_station`: neue Spalten `exclude_rules` (JSON, Voreinstellung Hörbuch-Genres), `allow_long`.
- Für die Genre-Suche: Hilfstabelle `module_radiostream_track_genres` (track_id, genre_key) beim Einlesen und
  einmalig nach der Migration befüllt (175.000 Titel, Hintergrundauftrag, gemessen werden muss die Dauer).

### Auswahl (rotation.py erweitern)
- `/feed/next` fragt der Reihe nach: Warteschlange → Programm (Playlist der Reihe nach/gemischt, oder Mix) → Alles.
- Mix/Alles: zufällige Stichprobe **innerhalb der Regel** (SQL mit den Regeln + Zufall), dann die Sperren wie heute.
  Leere Regel/leere Playlist/alle Titel fehlen → zurück zu „Alles“ und Hinweis im Sender-Kasten, nie Stille.
- Alles läuft über die Modul-DB, Liquidsoap bleibt fast unverändert (nur ggf. `prefetch`).

### Schnittstellen
- Lesen (Recht `module.radiostream`): Playlisten, Mixe, Programm, Warteschlange, `POST /mixes/preview` (Anzahl +
  Beispiele zu einer Regel).
- Ändern: Playlisten/Mixe anlegen, ändern, löschen; Programm wählen; Warteschlange. **Wer darf?** Siehe Frage unten.

### Oberfläche
- Neuer Reiter **„Programm“**: links Playlisten und Mixe, rechts der gewählte Eintrag (Titelliste bzw. Regel-Editor
  mit Live-Anzahl). Bibliothek bekommt „+ Playlist“, „Als Nächstes“, Ziehen auf die Seitenleiste.
- Reiter „Sender“: Kasten „Programm“ (Auswahl, was läuft), Kasten „Warteschlange“, Einstellung „Ausgeschlossen von
  Alles“.
- Ziehen mit der vorhandenen Ziehen-Bibliothek des Kerns, falls es eine gibt (prüfen), sonst HTML-Drag-and-drop;
  am Handy immer Knöpfe statt Ziehen. Texte de/en, Farben Farbstufen, eigene Dialoge.

## Prüfung
- Rot zuerst; Regeln (Mehrfach-Genres, Ausschließen, Jahrzehnte, Ordner), Playlist der Reihe nach/gemischt/am Ende,
  Warteschlange vor allem, fehlende Titel überspringen, nie Stille, Hörbücher nicht in „Alles“, Rechte.
- Mutanten, Gegenprobe, volle Reihe.
- **hydratest mit echter NAS-Bibliothek:** Mix „Rock“ (Anzahl gegen SQL prüfen), Playlist der Reihe nach im echten
  Stream (Reihenfolge an „Jetzt läuft“ ablesen), „Als Nächstes“ kommt wirklich als nächstes, Umschalten ohne Lücke,
  Hörbuch-Anteil in 100 Zufallstiteln = 0. Dauer der Genre-Hilfstabelle messen.
- E2E 1600/1280/393/375: Playlist anlegen, per Knopf und per Ziehen befüllen, umsortieren, als Programm wählen.

## Nicht in dieser Etappe
Uhrzeiten (Sendeplan, Etappe 5), Jingles zwischen Titeln (3c), Wünsche (3d), Playlisten-Import (M3U) – kann später
dazu.

## Offene Frage an Till
**Wer darf Playlisten/Mixe anlegen und das Programm umschalten?**
- A) nur Admins (Recht `radiostream.control`, wie die Sender-Einstellungen),
- B) zusätzlich Moderatoren (das Recht `radiostream.moderate` aus PLAN-E3.md kommt dann schon hier).
