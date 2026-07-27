# Mediacenter V3 — Treffer an Radarr/Sonarr übergeben

- Status: in Umsetzung
- Datum: 2026-07-27
- Baut auf: `SPEC-V1.md` (Suche/SABnzbd), `SPEC-V2.md` (Cover/Sprache)

## Ziel (tills Formulierung)

> „ich dachte das ich in hydra suchen kann und es an radarr oder sonarr
> übergeben kann"

Genau das: Die Suche bleibt im Mediacenter — mit Poster-Ansicht, Sprache und
Profilprüfung aus V1/V2. Neu ist ein **zweiter Übergabeweg**: statt direkt an
SABnzbd geht ein Treffer an Radarr bzw. Sonarr, die dann Download, Umbenennung
und Import in die Bibliothek übernehmen.

## Warum das der bessere Weg ist (Befund aus der Analyse)

Radarr, Sonarr und das Mediacenter benutzen **denselben Indexer und denselben
SABnzbd — mit denselben Kategorien**:

```
Mediacenter:      movie → "movies",  tv → "tv"
Radarr überwacht: "movies"           Sonarr überwacht: "tv"
```

Ein Direktdownload des Mediacenters landet damit in einer Kategorie, die Radarr
überwacht, ohne dass Radarr ihn bestellt hat. In tills Queue stehen genau solche
Fälle mit `importBlocked`:

> „Movie [X-Men (2000)][tt0120903] was not found in the grabbed release"

Diese 14 Blocker sind **vorbestehend** — das Mediacenter hat bisher null
Downloads gestartet (Queue und Historie leer). Der Konflikt wäre aber bei der
ersten Nutzung entstanden.

**Übergibt Radarr selbst den Download, kennt es ihn auch** und importiert
korrekt. Das Kategorie-Problem löst sich damit von selbst, statt durch
Sonderkategorien umgangen zu werden.

## Verifizierte Übergabe-Kette (live, lesend)

| Schritt | Radarr | Sonarr |
|---|---|---|
| 1. Titel identifizieren | `GET /movie/lookup?term=imdb:tt…` | `GET /series/lookup?term=tvdb:…` |
| 2. In Bibliothek? | `GET /movie?tmdbId=…` | `GET /series?tvdbId=…` |
| 3. Falls neu: anlegen | `POST /movie` | `POST /series` |
| 4. Release übergeben | `POST /release {guid, indexerId}` | dito |

Bestand: Radarr `indexerId=2`, Profile 1–6, Root `/mediadome/Plex_Filme`.
Sonarr `indexerId=3`, Profile 1–6, Root `/mediadome/Plex_Serien`.

Der Indexer ist in beiden Diensten derselbe wie im Mediacenter — die `guid`
eines Mediacenter-Treffers ist für Radarr/Sonarr also gültig.

## Etappen

### E1 — Übergabe an Radarr/Sonarr (dieser Schritt)

- Neuer Aufruf `POST /api/mediacenter/handoff` mit `result_id` + Zieldienst.
- Kette: Lookup → ggf. anlegen → Release übergeben.
- In der Trefferkarte ein zweiter Knopf neben „An SABnzbd übergeben":
  **„An Radarr übergeben"** bzw. **„An Sonarr übergeben"** — nur sichtbar, wenn
  der Dienst konfiguriert ist und der Medientyp passt (Film → Radarr, Serie →
  Sonarr).
- Ist der Titel noch nicht in der Bibliothek, wird er angelegt: Qualitätsprofil
  und Ordner wählt der Nutzer, mit den Werten des Dienstes als Vorauswahl.
  Kein Raten.
- Direktübergabe an SABnzbd bleibt erhalten (Bücher, Hörbücher, Musik kennen
  Radarr/Sonarr nicht).

### E2 — Bibliothek ansehen (später)

2099 Filme / 235 Serien mit Cover, Filter, Detailseite. Rein lesend.

### E3 — Verwalten (später, nur mit Bestätigungsgate)

Überwachen an/aus, Suche auslösen, Staffeln steuern. Schreibzugriff auf eine
große Bibliothek — braucht ein eigenes Rechtekonzept, bevor ein Agent das darf.

### E4 — Kalender/Wanted, E5 — Agent-Tools (später)

## Sicherheit

- Adresse und Schlüssel wie gehabt aus **einem** Credential (`radarr_token`,
  `sonarr_token`). Kein zweiter Konfigurationsort.
- Der Zieldienst kommt aus einer **festen Liste** (`radarr`/`sonarr`), nie aus
  freier Eingabe.
- Übergeben wird ausschließlich eine `result_id` aus der eigenen Suche — nie
  eine vom Client gelieferte URL oder `guid`. Damit bleibt die
  SSRF-Angriffsfläche unverändert.
- Die V1-Profilprüfung gilt weiter: nur `decision == "eligible"` ist
  übergabefähig.
- Anlegen eines Titels ist ein **schreibender** Zugriff. In E1 nur durch
  ausdrückliche Nutzeraktion in der Oberfläche; **kein Agent-Tool** — das folgt
  erst in E5 mit Bestätigungsgate.
- Schlüssel erscheinen nie in Antworten, Logs oder Fehlermeldungen.

## Akzeptanzkriterien

1. Bei einem Filmtreffer erscheint „An Radarr übergeben", bei einer Serie
   „An Sonarr übergeben".
2. Der Knopf fehlt, wenn der Dienst nicht konfiguriert ist.
3. Bei Büchern/Hörbüchern/Musik erscheint er nie.
4. Ein bereits in der Bibliothek vorhandener Titel wird nicht doppelt angelegt.
5. Ein neuer Titel wird mit dem gewählten Profil und Ordner angelegt.
6. Nach der Übergabe erscheint der Download in der Queue des Zieldienstes.
7. Eine abgelehnte Fassung (`rejected`) lässt sich nicht übergeben.
8. Ein nicht erreichbarer Dienst erzeugt eine klare Meldung, keinen Absturz.
9. Der Schlüssel erscheint in keiner Antwort.
10. Die Direktübergabe an SABnzbd funktioniert unverändert.
