# Mediacenter – Filme, Serien, Bücher und Musik suchen und herunterladen

Das Mediacenter durchsucht deinen Indexer **Treasure Maps**, prüft jeden Treffer nach festen Regeln und
übergibt deine Auswahl an **SABnzbd** zum Herunterladen. Filme und Serien kannst du auf Wunsch stattdessen an
**Radarr** bzw. **Sonarr** übergeben. Zugangsdaten, Treffer und Aufträge gehören jeweils dir allein.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne **Mediacenter** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Freizeit**).
   Fehlt noch ein Pflicht-Zugang, steht oben „Hinterlege zuerst die persönlichen Treasure-Maps- und
   SABnzbd-Zugangsdaten im Credential-Store.“ Ein Klick darauf öffnet die **Einstellungen**.
3. Dort führt **Zugangsdaten verwalten** zum Credential-Store. Lege je Dienst einen Eintrag an: Die Adresse des
   Dienstes gehört ins Feld URL/Muster, der API-Schlüssel in den Wert. Die Namen müssen genau so lauten:
   - `tresuere_token` für Treasure Maps (ja, mit dieser Schreibweise) – Pflicht
   - `sabnzb_token` für SABnzbd – Pflicht
   - `radarr_token` und `sonarr_token` – optional
4. Klicke im Mediacenter unter **Einstellungen** auf **Verbindungen testen**. Klappt alles, stehen bei Treasure Maps
   die erlaubte Trefferzahl je Suche und bei SABnzbd die Versionsnummer.
5. Wechsle zu **Suche**, wähle einen Medientyp, gib einen Titel ein und klicke **Suchen**.

## Was du damit machen kannst

### Suche
- Oben wählst du den Medientyp: **Filme**, **Serien**, **Bücher**, **Hörbücher**, **Hörspiele** oder **Musik**.
- Der Suchbegriff braucht mindestens 2 und höchstens 200 Zeichen. Gesucht werden kann erst, wenn Treasure Maps und
  SABnzbd eingerichtet sind.
- Du kannst einfach tippen, zum Beispiel „Matrix von 1999“ oder „Tatort S12E03“. Was die Suche daraus gelesen hat,
  zeigt sie unter **Verstanden:** als kleine Marken. Jahr, Staffel und Folge setzt sie als Filter ein, Staffel und
  Folge nur bei Serien. Was du selbst in die Filter einträgst, hat Vorrang. **Rückgängig** schreibt deine
  ursprüngliche Eingabe zurück ins Suchfeld.
- Das Mikrofon (**Per Sprache suchen**) erscheint nur, wenn dein Browser Spracheingabe kann. Es hört auf Deutsch.
- **Optionale Filter** klappt weitere Felder auf: **Jahr**, bei Serien **Staffel** und **Folge**, bei Büchern
  **Autor**, bei Musik **Künstler** und **Album**, außerdem **Maximales Alter in Tagen**, **Mindestgröße in MB** und
  **Maximalgröße in MB**. Ist ein Größen- oder Altersfilter gesetzt, fallen auch Treffer ohne Größen- bzw.
  Altersangabe heraus.

### Suchergebnisse
- Oben steht, wie viele Treffer das Profil erfüllen, und der Hinweis **Treffer sind 15 Minuten gültig**. Danach
  musst du neu suchen.
- Unter **Ansicht** wechselst du zwischen **Kachelansicht** (Standard) und **Listenansicht**.
- In der Kachelansicht ist ein Titel eine Kachel mit Cover, Jahr, Bewertung und der Zahl der passenden Fassungen.
  Fehlt ein Cover (bei Büchern meist), erscheint ein Symbol.
- Ein Klick auf die Kachel öffnet die Detailansicht mit Bild, Handlung, Genres und allen gefundenen Fassungen. Jede
  Fassung zeigt Größe, Alter, Sprache, Auflösung oder Format und eine Begründung, warum sie passt oder nicht.
  **Zurück zur Übersicht** führt zurück.
- Nur passende Fassungen bekommen den Knopf **An SABnzbd übergeben**. Abgelehnte bleiben sichtbar, aber ohne Knopf.
- Bei Filmen und Serien erscheint zusätzlich **An Radarr übergeben** bzw. **An Sonarr übergeben**, wenn du Radarr
  bzw. Sonarr eingerichtet hast. Dieser Knopf ist nur in der Detailansicht, nicht in der Listenansicht. Dann lädt
  Radarr bzw. Sonarr selbst herunter und sortiert die Datei in deine Bibliothek ein. Kennt der Dienst den Titel noch
  nicht, fragt das Mediacenter nach **Qualitätsprofil** und **Zielordner**; mit **Anlegen und übergeben** wird der
  Titel angelegt und übergeben, mit **Abbrechen** nicht.

### Die Regeln (Profile)
Jede Fassung wird geprüft:
- **Filme** und **Serien**: Deutsch muss bestätigt sein, Auflösung 1080p, 1080i oder 2160p (4K). 720p und weniger
  oder eine fehlende Auflösungsangabe fallen heraus, ebenso Kinomitschnitte wie CAM, Telesync, Telecine oder Screener.
- **Bücher**: Deutsch, als EPUB oder PDF.
- **Hörbücher** und **Hörspiele**: Deutsch, als MP3 oder M4B, keine Hörproben und keine unvollständigen Fassungen.
  Ist eine Fassung als Hörspiel gekennzeichnet, zählt sie nur unter Hörspiele, sonst nur unter Hörbücher.
- **Musik**: FLAC oder MP3, jede Sprache. Hast du **Künstler**, **Album** oder **Jahr** angegeben, rücken passende
  Fassungen nach oben.
- Treffer aus einer falschen Indexer-Kategorie fallen immer heraus.

Gibt es eine passende Fassung in 1080p und in 2160p (bei Musik: in FLAC und in MP3), steht dabei
„1080p oder 2160p direkt auswählen“ bzw. „FLAC oder MP3 direkt auswählen“. In der Oberfläche ist dein Klick diese
Auswahl.

### Warteschlange
Zeigt nur deine aktiven Aufträge, die über das Mediacenter gestartet wurden, mit Fortschritt, Geschwindigkeit und
**Restzeit**. Die Liste aktualisiert sich alle 10 Sekunden von selbst, sofort geht es mit **Aktualisieren**.

### Verlauf
Zeigt nur deine eigenen abgeschlossenen, fehlgeschlagenen oder manuell zu prüfenden Aufträge, zum Beispiel mit dem
Status **Fertig**, **Fehlgeschlagen** oder **Manuell prüfen**.

### Einstellungen
Eine Zeile je Dienst: **Indexer (Treasure Maps)**, **SABnzbd**, Radarr und Sonarr (die beiden letzten sind als
„optional“ markiert). Daneben steht, ob der Dienst eingerichtet ist und was der letzte Test ergab, und der Name des
passenden Eintrags im Credential-Store. Eintragen kannst du hier nichts: Adressen und Schlüssel stehen nur im
Credential-Store, **Zugangsdaten verwalten** führt dorthin. **Verbindungen testen** geht erst, wenn Treasure Maps und
SABnzbd eingerichtet sind.

## Mit Buddy und Agenten

Dein Buddy (und andere Haupt-Agenten) bekommt automatisch fünf Werkzeuge:
- `mediacenter_search` sucht. Es lädt nichts herunter.
- `mediacenter_enqueue` übergibt genau einen gefundenen, passenden Treffer an SABnzbd.
- `mediacenter_enqueue_batch` übergibt mehrere Treffer als Sammel-Download (bis zu 100).
- `mediacenter_queue` und `mediacenter_history` zeigen deine Warteschlange und deinen Verlauf.

Die Sicherung sitzt auf dem Server, nicht im Agenten:
- Suchen lädt nie. „Such mal Dune Part Two“ zeigt nur Treffer.
- Einzel-Download: Deine aktuelle Nachricht muss mit dem Download-Wunsch beginnen, zum Beispiel
  „Lade Dune Part Two herunter“ oder „Download Dune Part Two“. Außerdem muss sie den Titel nennen, mindestens zwei
  Wörter, und jedes Wort ab drei Buchstaben muss im Titel des Treffers stehen. Ein einzelnes Wort wie „Dune“ reicht
  nicht. Zusatzwörter wie „mal“, „runter“ oder die Kurzform „Lad“ stehen nicht im Titel und verhindern die
  Übergabe – „Lade“, „herunter“ und „bitte“ stören dagegen nicht.
- Auswahl 1080p/2160p oder FLAC/MP3: Gibt es beide, lehnt der Server die Übergabe zunächst ab und der Agent
  fragt nach. Antworte dann zum Beispiel „Nimm 2160p“ oder „Nimm FLAC“. Du kannst die Angabe auch gleich in den
  Download-Satz schreiben („Lade Dune Part Two in 2160p herunter“). „4K“ wird dabei nicht als Auswahl erkannt,
  schreib „2160p“ oder „UHD“.
- Sammel-Download: Deine Nachricht braucht ein Download-Wort, ein Wort wie „alle“, „sämtliche“ oder „komplett“
  und den Namen, zum Beispiel „Lad alle Alben von Cooper Alan runter“. Übernommen werden nur Treffer, deren Titel den
  Namen trägt, die anderen werden übersprungen. Treffer mit offener Auswahl (1080p/2160p oder FLAC/MP3) überspringt
  der Sammel-Download ebenfalls, die wählst du einzeln aus.
- Verneinungen („nicht“, „kein“) oder Fragen nach Übersetzung, Erklärung oder Vergleich lösen keinen Download aus.

Was nicht geht: An Radarr oder Sonarr übergeben kann nur die Oberfläche, dafür gibt es kein Werkzeug. Abgelehnte
Fassungen kann auch ein Agent nicht übergeben. Aufträge abbrechen oder löschen kann er nicht.

## Gut zu wissen

- Alles gehört dir: Zugangsdaten, Treffer und Aufträge sind an deinen Benutzer gebunden. Andere Nutzer sehen sie
  nicht, und Warteschlange und Verlauf zeigen nur, was über das Mediacenter lief.
- Doppelt übergeben geht nicht: Derselbe Treffer landet nur einmal in SABnzbd.
- Abbrechen oder Löschen eines Downloads geht nur direkt in SABnzbd, im Mediacenter gibt es dafür keinen Knopf.
- SABnzbd braucht die Kategorien `movies`, `tv`, `ebook`, `audiobook` und `audio`. Fehlen sie, meldet der Test
  „In SABnzbd fehlen benötigte Zielkategorien.“
- Typische Meldungen:
  - „Der Treffer ist abgelaufen (nach 15 Minuten). Bitte neu suchen und erneut übergeben.“
  - „Übergabestatus unklar. Bitte direkt in SABnzbd prüfen.“
  - „Zu viele Anfragen. Bitte kurz warten.“ – es gibt eine Grenze je Minute, zum Beispiel 30 Suchen und
    5 Übergaben.
  - „Treasure Maps hat den API-Schlüssel abgelehnt.“ bzw. „SABnzbd hat den API-Schlüssel abgelehnt.“ – Schlüssel im
    Credential-Store prüfen.
  - „Dem Treffer fehlt eine IMDb-/TVDB-Kennung — Zuordnung nicht möglich.“ – dann klappt nur die Übergabe an SABnzbd.

*Stand: Mediacenter 0.8.6, 22.11.2026*
