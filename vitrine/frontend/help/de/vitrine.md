# Vitrine – das Gehäuse-Display als kleine Bühne im Wohnzimmer

> Nur für eine bestimmte Hardware: Die Vitrine steuert ein USB-Display im Rechnergehäuse, das
> ArtInChip-Display (USB-Kennung 33c3:0e02), wie es zum Beispiel im Cooler Master MasterFrame 360 Stage LCD
> steckt. Ohne dieses Display zeigt die Vitrine nichts an.

Die Vitrine spielt auf dem Gehäuse-Display kurze Videos in Schleife und legt Uhr, Datum und eine Status-Leiste
darüber. Ein Kalender bestimmt, welches Video wann läuft, etwa zu Weihnachten oder im Sommer. Dazu kommen kurze
Einblendungen, eine Statuszentrale zum Anfassen per Maus und auf Wunsch die Beleuchtung im Gehäuse.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**. Dabei wird ein eigener Dienst
   eingerichtet, der das Bild auch dann weiterzeigt, wenn HydraHive neu startet.
2. Die Freigabe heißt „Vitrine (Gehäuse-Display)“ und gilt anfangs nur für Admins. In der Navigation erscheint
   **Vitrine** nur bei Admins (Gruppe **Arbeiten**, auf der Startseite im Bereich „Zuhause & Privat“).
3. Öffne **Vitrine**. Oben siehst du ein kleines Vorschaubild, den Zustand (zum Beispiel **Läuft**) und den
   Knopf **Speichern**.
4. Steht dort **Display nicht verbunden**, drücke links am Gehäuse-Display ein- bis zweimal den Knopf. Das
   Display wartet nach dem Einschalten oft darauf.
5. Lade im Reiter **Programm** unter **Videos** mit **Video hochladen** ein erstes Video hoch. Ohne Regeln
   laufen alle Videos im Wechsel.

## Was du damit machen kannst

Die Seite hat sechs Reiter. Ein gelber Punkt am Reiter heißt **nicht gespeichert**, ein roter Punkt
**ungültige Werte**. Änderungen wirken erst nach **Speichern**. Dann erscheint „Gespeichert – das Display
übernimmt es in wenigen Sekunden.“ Mit ungültigen Werten lässt sich nicht speichern.

### Übersicht
Links ein großes Vorschaubild, so wie das Display gerade aussieht. Rechts stehen der Zustand (**Läuft**,
**Dienst läuft nicht**, **Display nicht verbunden** oder einer der Nachtmodi), das laufende **Video**, die
gültige **Regel** (oder „keine (Standard)“), ein eventueller **Feiertag**, die **Bilder/s**, die Größe des
**Display** und der Zustand des **Dashboard**: „aus“, „bereit – Maus bewegen“, „wird gerade gezeigt“ oder
„nicht verfügbar“ mit Grund.

Darunter die **Einblendungen**: kurze Karten über der Status-Leiste des Displays. Du tippst einen Text (bis 280
Zeichen), wählst die **Art** (**Info**, **Erledigt**, **Warnung**, **Fehler**) und klickst **Einblenden**.
Bleibt das Feld leer, wird „Hallo vom Cockpit“ gezeigt. Die Liste zeigt, was gerade läuft und wie viele Sekunden
noch bleiben. Mit **Entfernen** (das X) nimmst du eine Karte weg. Fehler aus HydraHive und Meldungen aus
Butler-Flows erscheinen hier von selbst.

### Programm
- **Kalender**: Regeln legen fest, welche Videos wann laufen. Oben stehen fertige Vorlagen zum Anklicken, zum
  Beispiel Neujahr, Ostern, Halloween, die Adventssonntage, Weihnachten, Silvester, Chanukka, Ramadan und die vier
  Jahreszeiten. Mit **Neue Regel** baust du eine eigene. Jede Regel hat **Name**, **Art**, **Priorität (höher gewinnt)**,
  **Videos dieser Regel** und kann über **Aktiv** ein- und ausgeschaltet werden.
- Arten einer Regel: **Zeitraum im Jahr**, **Rund um Ostern**, **Advent**, **Einzelner Adventssonntag**,
  **Jahreszeit**, **Tageszeit**, **Bestimmter Wochentag im Monat** und **Termine je Jahr** (für Feste nach einem
  anderen Kalender, höchstens 40 Tage je Zeitraum und 40 Zeilen).
- Mit **Lichtfarbe bei diesem Anlass** kann eine Regel auch die Gehäuse-Beleuchtung einfärben.
- **Datum testen**: Datum und Uhrzeit wählen, **Testen** zeigt, welches Video mit welcher Regel dann liefe.
  **Auf dem Display zeigen** spielt das 30 Sekunden lang wirklich auf dem Display ab, danach geht es von selbst
  zurück. **Vorschau beenden** bricht vorher ab. Getestet werden die gespeicherten Einstellungen.
- **Videos**: hochladen und löschen (**Löschen**, dann **Wirklich löschen**). Erlaubt sind MP4, WebM, MKV oder
  MOV bis 500 MB. Hochformat 9:16 (1080×1920) sieht am besten aus. Videos aus dem Atelier passen direkt.

### Anzeige
- **Nachtmodus**: Mit **Nachts dunkel schalten** und den Uhrzeiten **Von**/**Bis** (Standard 23:00 bis 07:00)
  wählst du **Nachtmodus (gedimmte Uhr)**, **Nachtmodus (aus)** oder **Nachtmodus (Schlafvideos)**. Für
  Schlafvideos wählst du unter **Saisonale Nachtvideos** je Jahreszeit ruhige Videos. Fehlt eins, zeigt die
  Vitrine die gedimmte Uhr.
- **Mehrere Videos: wechseln alle (Minuten, 0 = nie)**: Standard 10 Minuten.
- **Bilder pro Sekunde**: 12 bis 30, Standard 24. Nach einer Änderung wird jedes Video einmal neu vorbereitet.
- **Einblendungen zeigen (Sekunden)**: 5 bis 120, Standard 15. Fehlerkarten bleiben länger.
- **Dashboard: zurück zum Video nach (Sekunden)**: 30 bis 1800, Standard 120, gezählt ohne Maus oder Klick.

### Statuszentrale
Bewegt jemand die Maus am Gehäuse-Bildschirm, wechselt das Display vom Video zur Statuszentrale. Mit
**Zurück zum Video** oder nach der eingestellten Ruhezeit kommt das Video zurück. Unter **Statuszentrale anpassen**
legst du fest, was sie zeigt:
- Bereiche **Meldungen**, **Zuhause**, **Hydra**, **Aufgaben**, **Rechner**, **Mining** und ein Bereich mit
  offenen Pull-Requests auf GitHub. Jeden Bereich kannst du ausblenden, mit **Nach oben**/**Nach unten**
  verschieben und unter **Auf welcher Seite** auf Seite 1, 2 oder 3 legen.
- Je Bereich gibt es Feineinstellungen, etwa **Unter „Neu“ voll anzeigen (1–5)**, die Räume bei **Zuhause**
  (Favoriten aus dem Home-Assistant-Modul), **Aufgaben von (Nutzer)**, **GitHub-Zugang aus Projekt** mit
  höchstens 5 Repos, oder bei Mining **In der Zeile „Rechner“ zeigen (spart Platz)**.
- **Chat am Gehäuse**: eine eigene Seite. Mit einer Bluetooth-Tastatur einfach lostippen, es antwortet der Buddy
  des Nutzers, der bei **Aufgaben von (Nutzer)** eingetragen ist.
- **Bluetooth am Gehäuse**: eine eigene Seite zum Suchen und Koppeln von Geräten. Entfernen geht nur im Cockpit.

### Beleuchtung
Steckt ein unterstützter Licht-Chip auf dem Mainboard, zeigt das Gehäuselicht, wie es Hydra geht. Es gilt immer
der wichtigste Zustand: Nacht, Fehler, Wartet, Fertig, Arbeitet, Anlass, Jahreszeit.
- **Beleuchtung steuern** schaltet das ein, **Nachts aus (Zeitfenster des Nachtmodus)** macht es nachts dunkel,
  **Helligkeit** gilt für alles.
- Unter **Zustände** stellst du je Zustand **Effekt** (**stehend**, **atmend**, **blinkend**, **aus**),
  **Farbe**, **Tempo** und eine eigene Helligkeit ein. Bei **Fehler** blinkt das Licht zuerst eine einstellbare
  Zeit, **Fertig** leuchtet nur kurz nach getaner Arbeit.
- **Farben nach Jahreszeit (aus = eine feste Ruhe-Farbe)**: je Jahreszeit eine Farbe, sonst eine feste Farbe für **Ruhe**.
- **Vorschau** zeigt einen Zustand 15 Sekunden lang am echten Licht.

### Bluetooth
Tastatur, Maus oder Kopfhörer am Server koppeln: **Gerät koppeln** öffnet die Suche für 2 Minuten, danach ist
der Server wieder unsichtbar. Gefundene Geräte koppelst du mit **Koppeln**. Fragt eine Tastatur nach einem Code,
tippst du ihn auf der Tastatur ein und drückst Enter. **Entfernen** löst ein Gerät wieder, es muss dann neu
gekoppelt werden.

### Arbeitsplätze
Hängt neben dem Gehäuse-Display ein normaler Bildschirm an einer eigenen Grafikkarte (zum Beispiel ein Fernseher),
kann der Rechner zwei Arbeitsplätze haben: die Vitrine auf dem Gehäuse-Display und einen zweiten Arbeitsplatz
mit eigenem Bildschirm, Ton, Tastatur und Maus. Ist so ein Bildschirm angeschlossen, zeigt die Karte **Zweiter
Arbeitsplatz** den Hinweis „Zweiter Bildschirm erkannt – als eigenen Arbeitsplatz einrichten?“.
- Die Vitrine läuft immer, auch wenn ein Bildschirm angeschlossen ist. Solange noch keine Zuordnung gespeichert ist,
  bleibt der Bildschirm an und zeigt eine Erweiterung der Vitrine-Oberfläche, aber noch keine eigene Anmeldung. Ordne
  die Geräte zu und klicke **Übernehmen**, dann **Zweiten Arbeitsplatz einschalten**.
- Die Vitrine liest Grafikkarten, Bildschirme, Ton und Eingabegeräte selbst aus und schlägt eine Zuordnung vor: Das
  USB-Display und eine Grafikkarte ohne Bildschirm bleiben bei der **Vitrine**, die Grafikkarte mit dem Bildschirm und
  ihr Ton gehen an **Zweiter Arbeitsplatz**.
- Bei Tastatur und Maus rät die Vitrine nicht, wenn sie es nicht sicher weiß. Dann steht dort „– bitte wählen –“ und
  du ordnest sie selbst zu.
- Jedes Gerät lässt sich in der Liste umstellen. **Übernehmen** speichert die Zuordnung. Das geht erst, wenn jedes
  Gerät zugeordnet ist, das USB-Display bei der Vitrine bleibt und jeder Arbeitsplatz genau eine eigene Grafikkarte hat.
- Fehlt das USB-Display, gibt es nur eine Grafikkarte oder keinen angeschlossenen Bildschirm, zeigt die Karte den Grund
  statt der Auswahl.
- **Zweiten Arbeitsplatz einschalten** (erscheint nach dem Übernehmen) stellt den Rechner um. Vorher fragt die Vitrine
  nach: Beide Bildschirme werden kurz schwarz. Danach meldet sich die Vitrine wie gewohnt selbst an, am zweiten
  Bildschirm erscheint ein normaler Anmeldebildschirm. Dafür richtet die Vitrine im Hintergrund einen anderen
  Anmeldedienst (lightdm) ein. Rechner mit nur einem Arbeitsplatz bekommen ihn nie.
- Vor dem Umschalten sichert die Vitrine die betroffenen Einstellungen. Klappt etwas nicht, stellt sie den Stand von
  vorher sofort wieder her, spätestens aber nach 5 Minuten von selbst, auch wenn das Umschalten hängen bleibt.
- **Zweiten Arbeitsplatz ausschalten** stellt den Stand von vorher wieder her (ein Arbeitsplatz, bisheriger
  Anmeldedienst).
- Solange der zweite Arbeitsplatz an ist, ändern Updates der Vitrine nichts an der Anmeldung.
- Ist eine Zuordnung gespeichert und der Bildschirm angeschlossen, schaltet jede Installation und jedes Update der
  Vitrine den zweiten Arbeitsplatz selbst ein, mit derselben Sicherung und Rücknahme wie beim Knopf. Das Ergebnis
  steht danach in der Karte.
- Hast du den zweiten Arbeitsplatz mit **Zweiten Arbeitsplatz ausschalten** bewusst ausgeschaltet, bleibt er auch nach
  Updates aus, bis du ihn wieder einschaltest. **Übernehmen** ändert daran nichts.
- Am zweiten Arbeitsplatz startet nach der Anmeldung der normale Desktop des Rechners (zum Beispiel Lubuntu). Die
  Vitrine liest ihn aus dem System. Wer eine andere Sitzung möchte, wählt sie im Anmeldebildschirm oben rechts; der
  Anmeldebildschirm merkt sich diese Wahl für den Nutzer und nimmt sie beim nächsten Mal wieder.
- Wird die Vitrine deinstalliert, schaltet sie den zweiten Arbeitsplatz vorher aus.
- Bluetooth-Geräte hängen am Funkchip des Rechners und bleiben bei der Vitrine.

## Mit Buddy und Agenten

Die Vitrine bringt das Werkzeug `display_message` mit. Es ist nicht automatisch an: Du gibst es einem Agenten
bewusst in seinen Einstellungen im Reiter **Tools & MCP**. Damit blendet der Agent eine kurze Karte auf dem
Display ein: Text bis 280 Zeichen, optional eine Überschrift bis 60 Zeichen, Stil info, success, warning oder
error und eine Dauer von 3 bis 600 Sekunden.

Was du fragen kannst:
- „Sag auf der Vitrine Bescheid, wenn das Backup fertig ist.“
- „Blende auf dem Gehäuse-Display eine Warnung ein, dass der Download hängt.“

Im **Butler** gibt es dazu die Aktion **Auf Vitrine anzeigen**. Text und Überschrift dürfen Platzhalter wie
`{{event.message_text}}` enthalten, dazu Stil und Sekunden.

Was nicht geht: Agenten können über die Vitrine keine Videos hochladen, keine Regeln ändern und das Licht nicht
schalten. Einblendungen sind reiner Text. Zu lange Texte werden mit „…“ gekürzt.

## Gut zu wissen

- Geheimnisse wie Zugangsdaten werden aus Einblendungen von Agenten und Butler vor dem Anzeigen entfernt.
- Gleiche Meldungen kurz hintereinander werden zusammengefasst und mit „×2“, „×3“ … gezählt. Höchstens drei
  Karten sind gleichzeitig auf dem Display.
- Fehler aus HydraHive erscheinen höchstens alle 10 Minuten je Quelle und höchstens 6 pro Stunde.
- Die Status-Leiste unten zeigt den Zustand von HydraHive, Last, Arbeitsspeicher, GPU-Temperatur, laufende
  Agenten und Fehler der letzten Stunde, soweit verfügbar.
- Die Statuszentrale per Maus wird bei der Installation eingerichtet, wenn Firefox und der Anmeldebildschirm SDDM
  vorhanden sind, auch wenn ein normaler Monitor am Rechner hängt (siehe **Arbeitsplätze**).
- Die Beleuchtung braucht OpenRGB und einen unterstützten Licht-Chip. Fehlt das, steht dort „Noch kein Stand vom
  Vitrine-Dienst (OpenRGB fehlt oder Dienst startet).“ oder „Beleuchtung nicht gefunden“. Die übrige Vitrine
  läuft trotzdem.
- **Bluetooth ist gerade nicht verfügbar (Vitrine-Dienst oder Adapter)**: Der Dienst läuft nicht oder es gibt
  keinen Bluetooth-Adapter. Bei **Sehr schwacher Empfang – Antennen am Rechner prüfen** die Antennen prüfen.
- „Die Einstellungen der Vitrine konnten nicht geladen werden.“: Die Seite hat keine Verbindung zum Modul.
  Seite neu laden.

*Stand: Vitrine 0.18.1, 24.11.2026*
