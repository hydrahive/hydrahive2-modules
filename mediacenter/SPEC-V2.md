# Mediacenter V2 — Cover-Oberfläche und natürlichsprachige Suche

- Status: umgesetzt (Modul-Version 0.5.0)
- Datum: 2026-07-27
- Baut auf: `SPEC-V1.md` (Newznab-Suche, SABnzbd, Agententools)

## Ziel

V1 ist funktional vollständig, sieht aber aus wie eine Textliste: 38 Backend-Module
stehen 714 Zeilen Frontend gegenüber. V2 macht aus dem Mediacenter eine Oberfläche
im Stil moderner Medienverwalter (Radarr/Sonarr) und verbessert die Suche.

Zwei Bausteine:

- **A — Cover-Oberfläche**: Poster, Backdrops, Bewertung, Genre, Handlung; Ergebnisse
  als Poster-Raster statt Textzeilen; Detailansicht je Titel.
- **C — Suche**: natürlichsprachige Eingabe („die neue Staffel Foundation auf Deutsch")
  und Spracheingabe per Mikrofon.

Baustein B (Radarr/Sonarr-Fernsteuerung) ist **bewusst nicht** Teil von V2 — siehe
„Bewusst nicht in V2".

## Ausgangsbefund (live verifiziert am 27.07.2026)

Der Indexer liefert bereits alle Metadaten mit, die für A nötig sind. Der Parser
verwirft sie derzeit. Ein Live-Abruf gegen Treasure Maps ergab:

| Medientyp | Verfügbare Attribute |
|---|---|
| Film | `coverurl`, `backdropurl`, `imdb`, `tmdb`, `imdbtitle`, `imdbyear`, `imdbscore`, `imdbplot`, `imdbactors`, `imdbdirector`, `genre`, `resolution`, `video`, `framerate`, `subs` |
| Serie | `coverurl`, `imdb`, `tmdb`, `tvdbid`, `tvmazeid`, `tvtitle`, `season`, `episode`, `tvepisodetitle`, `tvairdate` |
| Musik | `coverurl`, `artist`, `album`, `label`, `tracks`, `deezer` |
| Buch | *(keine Cover-Attribute)* |

Beispielwerte: `coverurl = https://picbit.io/movies_0242653-cover.webp`,
`imdbscore = 6.7`, `genre = Action, Adventure, Science Fiction, Thriller`.

**Folge:** Cover brauchen **keine externe API** — kein TMDB-Schlüssel, kein neuer
Netzwerkpfad, keine zusätzliche SSRF-Fläche. Bücher bekommen bewusst kein Cover
(der Indexer liefert keins); dort greift eine Typ-Illustration als Platzhalter.

## Sicherheit

### Secret-Leak-Prüfung (Befund aus der Analyse)

Der Indexer spiegelt den API-Schlüssel in `link` und `enclosure url` zurück. Der
reguläre Suchpfad ist dicht — `redaction.release_contains_secret()` sortiert
betroffene Releases aus, im API-Ergebnis erscheint der Schlüssel nicht (verifiziert).

**Verbindlich für V2:** Jedes neue Feld, das aus dem Indexer stammt, muss durch
denselben Filter. `release_contains_secret()` wird um die neuen Felder erweitert —
sonst reißt der Ausbau das Loch wieder auf. Ein Test nagelt das fest.

### Cover-URLs

- Nur `https`, kein Benutzer/Passwort, keine Fragmente, max. 2048 Zeichen.
- Host-Allowlist analog `download_urls.safe_download_url` (`picbit.io` +
  Indexer-Hosts). Alles andere → kein Cover, kein Fehler.
- Query-Parameter werden **verworfen** (dieselbe Regel wie beim NZB-Abruf) —
  darüber könnte sonst ein Schlüssel mitreisen.
- Das Frontend lädt Cover direkt vom Bildhost (kein Proxy). `referrerPolicy="no-referrer"`
  verhindert, dass HydraHive-URLs an den Bildhost lecken. Ein defektes Bild fällt
  auf den Platzhalter zurück.

### Natürlichsprachige Suche

Der Parser läuft **rein lokal und regelbasiert** — kein LLM-Aufruf, keine Daten
verlassen den Server. Begründung: die Suche muss offline funktionieren und darf
keine Kosten pro Tastendruck erzeugen. Bei Mehrdeutigkeit gewinnt die explizite
Auswahl des Nutzers; der Parser schlägt nur vor und zeigt sichtbar, was er
verstanden hat.

## A — Cover-Oberfläche

### Backend

`RawRelease` und `SearchResultOut` bekommen ein optionales `meta`-Objekt:

```
ReleaseMeta:
  cover_url, backdrop_url : str | None   (validiert, sonst None)
  title_clean             : str | None   (imdbtitle/tvtitle — echter Titel statt Release-Name)
  year                    : int | None
  score                   : float | None (0..10)
  genres                  : list[str]    (max 5)
  plot                    : str | None   (max 500 Zeichen)
  imdb_id, tmdb_id, tvdb_id : str | None
  season, episode         : int | None   (Serie)
  artist, album, label    : str | None   (Musik)
```

Regeln:

- Alle Felder sind optional. Fehlt alles, bleibt `meta = None` — die Oberfläche
  funktioniert wie bisher.
- Längen werden hart begrenzt (Plot 500, Genre 5×40, Titel 200).
- Ungültige Werte werden still verworfen, nie geraten.
- Der Parser bleibt strikt: unbekannte Attribute werden ignoriert, kein Feld wird
  aus dem Release-Titel „geschätzt".

### Gruppierung

Suchergebnisse werden nach Titel gruppiert (Schlüssel: `imdb_id` bzw. `tmdb_id`,
sonst normalisierter Titel+Jahr). Ein Film mit acht Releases erscheint als **eine**
Karte mit acht Fassungen — statt achtmal in der Liste. Das ist der eigentliche
Radarr-Effekt.

Innerhalb einer Gruppe werden die Fassungen nach dem bestehenden `score` sortiert;
die beste zulässige Fassung ist vorausgewählt.

### Frontend

- **Poster-Raster** als Standardansicht: Cover, Titel, Jahr, Bewertung, Anzahl Fassungen.
- **Listenansicht** bleibt als Umschaltoption erhalten (schnelleres Scannen, und sie
  ist die einzige sinnvolle Darstellung für Bücher ohne Cover).
- **Detailansicht** (Klick auf Karte): Backdrop als Kopfbild, Handlung, Genre,
  Bewertung, darunter die Fassungen mit Größe/Auflösung/Sprache/Score und dem
  bestehenden Herunterladen-Knopf inklusive aller V1-Profilregeln.
- Cover werden lazy geladen (`loading="lazy"`), mit Seitenverhältnis 2:3 und
  Platzhalter, damit das Raster nicht springt.

**Die Profil- und Freigabelogik aus V1 bleibt unverändert.** V2 ändert nur die
Darstellung, nicht die Entscheidung, was heruntergeladen werden darf.

## C — Suche und Sprache

### Natürlichsprachige Eingabe

Ein lokaler Parser (`query_parser.py`) zerlegt freien Text in strukturierte Filter:

| Eingabe | Erkannt |
|---|---|
| „Matrix von 1999" | query=Matrix, year=1999 |
| „Foundation Staffel 2 auf Deutsch" | query=Foundation, media_type=tv, season=2 |
| „Foundation S02E05" | query=Foundation, media_type=tv, season=2, episode=05 |
| „Hörbuch Der Hobbit" | query=Der Hobbit, media_type=audiobook |
| „Album Rammstein Zeit als FLAC" | media_type=music, artist/album, Format-Hinweis |
| „Matrix in 4K" | query=Matrix, Auflösungswunsch 2160 |

Regeln:

- Deutsch **und** Englisch (Staffel/Season, Folge/Episode, Jahr/year).
- Der Parser **entfernt** erkannte Teile aus dem Suchbegriff, damit der Indexer
  einen sauberen Titel bekommt (heute scheitert „Matrix von 1999" daran, dass
  „von 1999" mitgesucht wird).
- Was erkannt wurde, wird als abnehmbare Chips angezeigt — der Nutzer sieht und
  korrigiert die Interpretation. Keine unsichtbare Magie.
- Erkennt der Parser nichts, verhält sich alles exakt wie heute.
- Der Medientyp aus dem Text setzt die Auswahl nur, wenn der Nutzer nicht selbst
  eine getroffen hat.

### Spracheingabe

Mikrofonknopf im Suchfeld über die Web Speech API des Browsers (`de-DE`),
Ergebnis geht durch denselben Parser.

- Rein clientseitig, kein Upload, keine Kosten, keine Server-Abhängigkeit.
- Der Knopf erscheint **nur**, wenn der Browser die Schnittstelle unterstützt
  (Chrome/Edge ja, Firefox nein) — kein toter Knopf.
- Bestehende Whisper-Infrastruktur wird bewusst **nicht** genutzt: sie würde
  Audio-Upload, Kosten und einen Serverpfad bedeuten, wo der Browser es
  kostenlos und lokal kann. Falls sich das als unzureichend erweist, ist Whisper
  ein späterer Austausch hinter derselben Schnittstelle.

## Live-Verifikation (27.07.2026)

Gegen den echten Indexer, kompletter Weg Eingabe → Parser → Suche → Gruppierung:

```
EINGABE : "Matrix von 1999"
VERSTAND: query='Matrix' jahr=1999 chips=['year']
30 Treffer -> 1 Titel
  [COVER] The Matrix (1999) ★8.7 · 30 Fassungen
          Set in the 22nd century, The Matrix tells the story of…
SERIE   : "Foundation Staffel 2" -> query='Foundation' staffel=2
```

Schlüssel-Leak-Prüfung im Ergebnis: negativ.

**Wichtiger Befund während der Umsetzung:** Der Indexer liefert die
Zusatzattribute nur mit `extended=1`. Ohne diesen Parameter wäre der gesamte
Cover-Ausbau wirkungslos geblieben — `build_search_params` sendet ihn jetzt,
ein Test nagelt das fest.

Zweiter Befund: Der generische 512-Zeichen-Deckel für Attributwerte hätte jedes
Release mit langer Handlungsbeschreibung **komplett verworfen**. Fließtext wird
jetzt gekürzt statt den Treffer zu verschlucken (Grenze 4096, dann gilt der Wert
als kaputt).

## Akzeptanzkriterien

1. Eine Filmsuche zeigt Poster mit Titel, Jahr und Bewertung statt einer Textzeile.
2. Ein Film mit mehreren Fassungen erscheint als eine Karte mit Fassungsanzahl.
3. Die Detailansicht zeigt Handlung, Genre und Bewertung sowie alle Fassungen.
4. Bücher ohne Cover werden sauber mit Platzhalter dargestellt, nichts bricht.
5. Der API-Schlüssel erscheint in keinem neuen Feld (Test).
6. Cover-URLs außerhalb der Allowlist werden verworfen (Test).
7. „Foundation Staffel 2 auf Deutsch" erzeugt query=Foundation, media_type=tv, season=2.
8. Der Suchbegriff enthält die erkannten Zusätze nicht mehr.
9. Erkannte Filter sind sichtbar und einzeln abwählbar.
10. Ohne Browser-Unterstützung erscheint kein Mikrofonknopf.
11. Alle V1-Profilregeln und Freigaben gelten unverändert.

## Bewusst nicht in V2

- **Radarr/Sonarr-Fernsteuerung.** Keine der beiden Anwendungen läuft in dieser
  Umgebung (geprüft: keine Container, keine Ports, keine Zugangsdaten). Eine
  Fernbedienung für ein nicht vorhandenes Gerät zu bauen, wäre verfrüht. Der
  eigentliche Nutzen (Abonnements, automatische Suche nach neuen Folgen) lässt
  sich später nativ im Mediacenter bauen — ohne zweiten Dienst und ohne doppelte
  Oberfläche. Entscheidung vertagt, nicht verworfen.
- Abonnements/Watchlist, Kalender kommender Folgen.
- Externe Metadaten-Anbieter (TMDB/TVDB direkt).
- Löschen/Abbrechen von Aufträgen (unverändert aus V1).
- Lokale Bibliotheksverwaltung, Abspielen, Formatumwandlung.
