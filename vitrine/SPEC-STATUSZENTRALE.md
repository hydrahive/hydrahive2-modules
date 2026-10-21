# Vitrine — Statuszentrale und Wechsel (freigegeben von Till am 18.10.2026)

## Was

Das Gehäuse-Display zeigt wie bisher die Feiertagsschleife. **Bewegt jemand die Maus**, die an .2 angeschlossen ist, schaltet es
auf ein **Dashboard** um: eine Hochkant-Webseite mit dem Zustand von HydraHive. Danach geht es von selbst zurück zum Video.
Eine Einblendung (Karte) erklärt bei Bedarf: „Maus bewegen für Details“.

## Warum

Die Status-Leiste und die Karten reichen für „läuft/Fehler“, aber nicht für „was genau, und was soll ich tun“.
Till will Meldungen sehen, ohne am Rechner zu sitzen. Später sollen dort auch Zuhause, Chat und Knöpfe dazukommen.

## Gemessen (Machbarkeitstest 18.10.2026 auf .2, nicht angenommen)

| Punkt | Ergebnis |
|---|---|
| EVDI auf Ubuntu 26.04, Kernel 7.0.0-38 | Paket `linux-modules-evdi-generic` (von Canonical signiert) und `libevdi1` 1.14.15, kein Selbstbau |
| Display als Monitor | eigene EDID 1080×1920 bei 60 Hz → in X als `DVI-I-2-1`, Bild kommt am Display an |
| Last | Brücke (EVDI → JPEG → USB) bei Vollbild-Video ≈ 12,7 % eines Kerns bei ≈ 15,7 Bildern/s. Ohne Bildänderung ≈ 0, weil nur geänderte Bilder geschickt werden |
| X-Server | Der laufende sddm-Xorg (Anmeldebildschirm) übernimmt die EVDI-Karte von selbst. Ein **zweiter** Xorg auf derselben Karte scheitert (`drmSetMaster: busy`) |
| Risiko | Ohne eigene Sitzung zeigt das Display den sddm-Anmeldebildschirm **mit Benutzernamen** |
| Eingabe | Der X-Server hat die Erweiterung `MIT-SCREEN-SAVER` (Leerlaufzeit abfragbar). An .2 hängt ein **Apple Magic Trackpad** (meldet sich als Maus) |

## Wie

### Ein Dienst, zwei Quellen

Der Vitrine-Dienst bleibt der **einzige**, der Bilder an das Display schickt (das kann nur ein Programm gleichzeitig).
Er bekommt eine zweite Quelle:

| Modus | Quelle | Overlay |
|---|---|---|
| `video` (Standard) | Feiertagsschleife wie bisher (Bildcache, ≈ 9 % eines Kerns) | Uhr, Datum, Status-Leiste, Karten |
| `dashboard` | Bild des virtuellen Monitors (EVDI), nur geänderte Bilder, höchstens 20 Bilder/s | keins, die Seite zeigt alles selbst |

- **Umschalten auf Dashboard:** Der Dienst fragt jede ¼ s die Leerlaufzeit des Kiosk-X-Servers ab (XScreenSaver-Erweiterung).
  Liegt die letzte Eingabe (Maus, auch Klick oder Tastatur) unter 1 s, wird umgeschaltet.
- **Zurück zum Video:** nach **2 Minuten** ohne Eingabe (im Cockpit einstellbar, 30 s – 30 min) oder über den Knopf „Zurück“ auf der Seite.
- **Nachtmodus:** Auch nachts weckt die Maus das Dashboard. Nach der Rückkehrzeit geht es zurück zum Nachtbild.
- Fällt EVDI oder der Kiosk aus, bleibt der Dienst im Modus `video`. Das Dashboard ist eine Zugabe, kein Muss.

### Kiosk-Sitzung statt Anmeldebildschirm

- Eigener Systemnutzer `hydrahive-kiosk` ohne Passwort und ohne Shell-Anmeldung, Mitglied von `video`/`input`.
- sddm meldet ihn **automatisch** in eine eigene Sitzung „Vitrine-Kiosk“ an: Openbox ohne Leisten und darin ein Browser im Kiosk-Modus
  (Vollbild, keine Adressleiste), der `http://127.0.0.1:<port>/vitrine/dashboard` zeigt. Stürzt der Browser ab, startet die Sitzung ihn neu.
- Folge: Auf .2 gibt es dann **keinen grafischen Anmeldebildschirm** mehr. An .2 hängt sonst kein Monitor, gearbeitet wird per SSH.
  Rückbau: ein Schalter im Cockpit oder das Deinstallieren des Moduls stellt sddm wieder auf normal.
- Der Mauszeiger ist nur im Dashboard sichtbar.

### Dashboard-Seite (Hochformat 1080×1920, vom Sofa lesbar)

V1 = **Statuszentrale**, nur lesen:

| Bereich | Inhalt |
|---|---|
| oben | aktuelle Meldung (falls eine Karte läuft), groß und mit Volltext |
| Hydra | läuft/Fehler, laufende Agenten (Name, seit wann), Fehler der letzten Stunde (Quelle und kurzer Text) |
| Arbeit | offene Tasks (Zahl, die 5 wichtigsten Titel), was auf Till wartet (PRs mit Status „wartet auf OK“, CI rot/grün) |
| Rechner | CPU, RAM, GPU-Temperatur, Platte, Uptime von .2 |
| Mining | an/aus, €/Tag (nur wenn das Mining-Modul installiert ist) |
| unten | Uhr, Datum, Knopf „Zurück zum Video“ |

- Die Seite fragt alle 5 s eine **eigene Daten-Route** des Moduls ab (`GET /api/modules/vitrine/dashboard/data`).
- Zugang: eigener **Kiosk-Schlüssel** (zufällig, Datei 0600 beim Kiosk-Nutzer), gilt **nur** für diese eine Route und **nur von 127.0.0.1**.
  Kein Login, keine anderen Rechte.
- Die Route liefert nur Zusammenfassungen: keine Chat-Inhalte, keine Secrets (Schwärzung wie bei den Karten), Texte gekürzt.

### Meldungen

- Karten (Einblendungen) bekommen eine zweite Zeile „🖱 Maus bewegen für Details“, aber nur wenn das Dashboard verfügbar ist.
- Im Dashboard steht die Meldung oben, mit Knopf „Gelesen“ (entfernt die Karte). Das ist der **einzige** Knopf, der etwas ändert.

## S2 — Statuszentrale mit Daten (freigegeben von Till am 19.10.2026, abgenommen am Gehäuse am 19.10.2026, vitrine 0.8.1)

S1 ist abgenommen (Till, 19.10.): Maus → Dashboard, „Zurück“, Rückkehr nach 2 min. S2 ersetzt die Platzhalter-Seite durch
die echte Statuszentrale. Weiterhin **nur lesen**.

### Daten (Quellen am 19.10. auf .2 geprüft)

| Bereich | Inhalt | Quelle |
|---|---|---|
| Meldung | die neueste sichtbare Karte (Titel, Volltext, Art) | `<daten>/inbox` (wie die Karten) |
| Hydra | Dienst läuft/Fehler, laufende Agenten (Anzahl), Fehler der letzten Stunde: je Quelle Anzahl + letzter Text | `hydrahive.runner.concurrency.active_count()`, Tabelle `errors_log` (wie `notify.py`) |
| Aufgaben | offene + laufende Tasks (Zahl), die 5 wichtigsten Titel (Priorität, dann Alter) | Tabelle `module_tasks` des Besitzers (s. u.) – nur wenn das Modul `tasks` installiert ist |
| Rechner | Last, RAM, GPU-Temperatur, freier Platz `/`, Laufzeit | wie die Status-Leiste (`renderer/sysinfo.py`) + `shutil.disk_usage`, `/proc/uptime` |
| Mining | Rechner an/aus, geschätzt €/Tag jetzt | Tabellen `module_mining_*` – nur wenn das Modul `mining` installiert ist |
| Wartet auf Till | offene PRs von hydrahive2.0 + hydrahive2-modules (Nummer, Titel, CI grün/rot/läuft, „mergebar“) | GitHub-REST, nur lesend, mit dem Token des Projekts „Hydrahive DEV“ (s. u.) |
| Uhr | Uhrzeit, Datum, Feiertag | Browser + Vitrine-Programm |

### GitHub („Wartet auf Till“)
- Token: der Git-Token des HydraHive-Projekts **Hydrahive DEV** (am 19.10. auf .2 geprüft: hinterlegt für die Repos
  hydrahive2 und hydrahive2-modules; HydraHive gibt ihn den Projekt-Agenten als `GH_TOKEN`). Projekt im Cockpit wählbar.
- Der Token hat Schreibrechte (Push/Merge). Die Vitrine nutzt ihn **nur für GET** auf `api.github.com`, feste Pfade
  (`/repos/<owner>/<repo>/pulls?state=open`, Check-Runs des Head-Commits), höchstens 1× pro Minute, Zeitlimit 10 s.
- Der Token verlässt das Backend nie (nicht in der Antwort, nicht im Log, nicht im Cockpit). Repos fest auf
  `hydrahive/hydrahive2.0` und `hydrahive/hydrahive2-modules` (im Cockpit änderbar, nur `owner/repo`-Form).
- Fehlt der Token oder antwortet GitHub nicht → Bereich zeigt „GitHub nicht erreichbar“, Rest unverändert. Scheitert nur
  ein Repo, bleiben die PRs der anderen stehen und der Hinweis nennt das Repo (Abnahme 19.10.: falscher Repo-Name → 404).
- Nach einem Modul-Update startet der Installer den Kiosk-Firefox neu, damit die neue Seite geladen wird (Abnahme 19.10.).

### Wem gehören die Tasks?
Der Kiosk hat keinen Nutzer. Die Tasks kommen vom **Besitzer** der Vitrine: einstellbar im Cockpit (Feld „Tasks von“,
Auswahl der HydraHive-Nutzer, Standard = der Admin, der zuletzt die Vitrine-Einstellungen gespeichert hat).

### Route + Sicherheit
- `GET /api/module-device/vitrine/data?k=…` — gleiche Prüfung wie S1 (Kiosk-Schlüssel + direkte Verbindung von 127.0.0.1,
  Rate-Limit des Kerns). Antwort ist eine **feste Liste** von Feldern (Schema im Backend), nichts Freies.
- Texte (Task-Titel, Fehlermeldungen, Karten) laufen durch die Secret-Schwärzung (`credentials.redaction.scrub`, wie
  `notify.py`) und werden gekürzt (Titel 80, Fehler 140 Zeichen). Keine Chat-Inhalte, keine Session-Titel, keine Pfade aus
  Tracebacks.
- Fehlt ein Modul (tasks, mining) oder eine Quelle scheitert, fehlt nur dieser Bereich (`null`), die Route antwortet trotzdem.
- Die Daten werden im Backend höchstens alle 5 s neu berechnet (Zwischenspeicher), egal wie oft die Seite fragt.

### Seite
- Statische HTML-Seite aus dem Modul (`backend/kiosk_page.html`, CSS + kleines Skript, keine externen Dateien), lädt
  `data` alle 5 s. Hochkant 1080×1920, Schrift vom Sofa lesbar (Zahlen ≥ 64 px, Text ≥ 32 px).
- Knopf „Zurück zum Video“ unten (wie S1). Keine weiteren Knöpfe.
- Fehlt die Verbindung zum Backend: Hinweis „HydraHive antwortet nicht“ statt leerer Felder.

### Akzeptanz S2
- Alle Bereiche zeigen echte Werte von .2 (Abgleich mit Cockpit/Tasks/Mining-Seite)
- Route: ohne/falscher Schlüssel, andere Adresse → 404 (Tests); fehlendes tasks-/mining-Modul → Bereich `null` (Tests)
- Ein Secret in einer Fehlermeldung erscheint geschwärzt (Test)
- Seite ruhig: Firefox < 5 % eines Kerns (gemessen 60 s); Backend-Last durch `data` vernachlässigbar (Zwischenspeicher)

### Entscheidungen S2 (Till, 19.10.2026)
1. Tasks vom Nutzer **till** (im Cockpit änderbar).
2. Mining-Bereich **ja**, wenn das Modul installiert ist.
3. „Wartet auf Till“ **ja**, mit dem Token des Projekts **Hydrahive DEV** (nur lesend genutzt).

## S3 — Meldungen mit Verlauf (Entscheidung Till 19.10.2026: Option C; abgenommen am Gehäuse am 19.10.2026, vitrine 0.9.1)

S2 ist abgenommen (Till, 19.10.: „alles lesbar und plausibel“; Firefox 0,5 % eines Kerns über 60 s). S3 sorgt dafür, dass
eine Meldung nicht verloren geht: Auf dem Video bleibt die Karte wie heute (15 s, Fehler 10 min). In der Statuszentrale
steht sie aber **24 Stunden** lang, bis Till sie als gelesen markiert.

### Ausgangslage (Code am 19.10. geprüft)
- `renderer/inbox.py`: eine Datei je Meldung, gleiche Meldung binnen 60 s wird gezählt (×2), höchstens 3 sichtbar,
  höchstens 100 Dateien. `active()` **löscht** abgelaufene Karten sofort, deshalb gibt es heute keinen Rückblick.
- Cockpit: `DELETE /messages/{id}` (Admin) entfernt eine Meldung.
- `state.dashboard` = „bereit“ / „nicht verfügbar: …“ / „aus“ (`play_dashboard`).

### Lebensdauer einer Meldung
| Zeit | Video (Karte) | Statuszentrale |
|---|---|---|
| bis `expires` (wie heute) | sichtbar, höchstens 3 | unter **Neu** |
| danach bis 24 h nach `created` | weg | unter **Neu**, solange ungelesen; sonst unter **Verlauf** |
| älter als 24 h | – | gelöscht (beim nächsten Lesen der Ablage) |

- Neues Feld `read` (Zeit oder `null`) in der Meldungsdatei. Alte Dateien ohne das Feld gelten als ungelesen.
- **Gelesen** heißt: `read` wird gesetzt, und die Karte verschwindet auch sofort vom Video. Löschen kann weiterhin nur
  das Cockpit.
- Kommt dieselbe Meldung nach dem Lesen erneut (Zählung binnen 60 s), ist sie wieder ungelesen (`read = null`, Zähler +1).
- Der Ordner bleibt auf 100 Dateien begrenzt (die ältesten fallen raus), egal ob gelesen.

### Karte auf dem Video
- Zweite Zeile „🖱 Maus bewegen für Details“, **nur** wenn die Statuszentrale verfügbar ist
  (`state.dashboard == "bereit"`). Sonst bleibt die Karte wie heute.

### Statuszentrale
- Oben **Neu (n)**: ungelesene Meldungen der letzten 24 h, neueste zuerst, höchstens 5 mit Volltext (Titel, Art, Uhrzeit,
  ×Zähler), darunter „+ n weitere“. Je Meldung ein Knopf **Gelesen**.
- Darunter **Verlauf**: gelesene Meldungen der letzten 24 h, höchstens 10, je eine Zeile (Uhrzeit, Titel/Text gekürzt).
- Keine Meldung → der Bereich zeigt „Keine neuen Meldungen“, und der Verlauf ist nur sichtbar, wenn er Einträge hat.
- Kein „Alle gelesen“ (bewusst; kann später kommen).

### Daten + Route
- `/data` liefert statt `message` den Bereich `messages` = `{"new": [...], "new_count": n, "history": [...]}`. Je Eintrag
  `id`, `title`, `text`, `kind`, `count`, `time` (HH:MM). Texte wie in S2 geschwärzt und gekürzt (Titel 80; Volltext höchstens
  280 wie in der Ablage). Zwischenspeicher wie S2 (5 s), wird nach „Gelesen“ sofort verworfen.
- Neu: `POST /api/module-device/vitrine/read?k=…`, gleiche Prüfung wie S1/S2 (Kiosk-Schlüssel + direkte Verbindung
  von 127.0.0.1, Rate-Limit des Kerns). Körper nur `{"id": "<12 Hex-Zeichen>"}` (alles andere → 422). Die ID wird nur
  verglichen, nie zu einem Pfad. Unbekannte ID → 404. Antwort 204.
- „Gelesen“ und „Zurück“ bleiben die **einzigen** Kiosk-Routen, die etwas ändern.

### Abnahme S3 (19.10.2026, vitrine 0.9.1)
- Till: zwei Meldungen aus dem Cockpit (14:21, 14:23) → Karte → Maus 20–30 s kräftig bewegt → Neu → Gelesen (zweimal
  204) → Verlauf. „Hat alles geklappt, nicht eingefroren.“
- Gemessen 14:21–14:27 jede Sekunde: X immer frei (ep_poll), 0 × `flip_done`, EVDI-Thread nie im Warten auf X;
  Firefox 0,4 % eines Kerns.
- Vorher (0.9.0) fror die Statuszentrale bei Mausbewegung ein: Der EVDI-Thread fragte X nach dem Zeiger, X hing im
  EVDI-Bildwechsel → gegenseitiges Warten. Behoben in 0.9.1 (eigener Zeiger-Thread, PR #212).

### Akzeptanz S3
- Meldung abschicken (Cockpit oder Werkzeug) → Karte auf dem Video mit Zeile „Maus bewegen …“; Maus → steht unter Neu
- Nach Ablauf der Karte steht sie weiter unter Neu; „Gelesen“ → in den Verlauf, Zähler sinkt, Karte (falls noch da) weg
- 24 h alte Meldungen verschwinden (Test mit fester Uhr); gleiche Meldung nach dem Lesen → wieder Neu, ×2
- Route `read`: ohne/falscher Schlüssel, andere Adresse → 404; kaputter Körper → 422; unbekannte ID → 404 (Tests)
- Statuszentrale nicht verfügbar → Karte ohne zweite Zeile (Test)
- Seite weiter ruhig: Firefox < 5 % eines Kerns über 60 s

## S4 — Zuhause + Anordnung (Entscheidungen Till 19.10.2026; abgenommen am Gehäuse am 19.10.2026, vitrine 0.10.0)

S3 ist abgenommen. S4 bringt zwei Dinge: einen Bereich **Zuhause** mit den Home-Assistant-Favoriten und eine
**Einstellungsseite**, auf der Till festlegt, welche Bereiche in welcher Reihenfolge erscheinen. Ziel laut Till:
aufgeräumt, nicht vollgestopft. Weiterhin **nur lesen**, keine Schalter.

### Ausgangslage (am 19.10. auf .2 geprüft)
- HA-Modul 1.0.4 ist installiert, URL und Token stehen in den System-Einstellungen. Till hat 12 Favoriten in
  `module_homeassistant_favorites`: 4 Thermometer (Temperatur, Luftfeuchte, Batterie) und 1 Steckdose (Energie),
  in HA den Räumen Wohnzimmer, Schlafzimmer, Küche und Alex Zimmer zugeordnet. Alex Zimmer ist seit etwa 13 h nicht
  erreichbar.
- Platz: Mit 5 langen Meldungen reicht die Seite bis 1890 von 1920 px (S3-Messung).

### Bereich „Zuhause“
- Eine Zeile **je Raum** (HA-Bereich), sortiert wie die Favoriten. Inhalt: Temperatur, Luftfeuchte und sonst den ersten
  weiteren Wert kurz am Ende (z. B. Energie).
- **Batterie** nur, wenn unter 20 %. Dann steht „Batterie 15 %“ in Gelb.
- **Nicht erreichbar** (alle Werte des Raums `unavailable`/`unknown`): graue Zeile „nicht erreichbar seit 13 h“.
  Sind nur einzelne Werte weg, werden sie weggelassen.
- Favoriten ohne Raum kommen unter „Sonstiges“.
- Quelle: die Favoriten des Besitzers der Statuszentrale (`tasks_user`, Standard `till`) aus der Tabelle, und die Werte
  über den **Client des HA-Moduls** (`hhmod_homeassistant.client.render_template`), mit **einem** festen Template für
  alle Favoriten (Name, Raum, Art, Wert, Einheit, letzte Änderung). Die Entity-IDs werden vorher geprüft
  (`^[a-z_]+\.[a-z0-9_]+$`). Die Vitrine hält **keinen eigenen HA-Zugang**, Token und Adresse bleiben im HA-Modul.
- Ist das HA-Modul nicht geladen, fehlt die Tabelle oder antwortet HA nicht → Bereich `null` (S2-Regel), bzw.
  „Home Assistant nicht erreichbar“.
- Zwischenspeicher **60 s** (Raumtemperaturen ändern sich langsam, HA wird geschont).

### Einstellungsseite „Statuszentrale anpassen“ (Cockpit, Vitrine-Seite)
- Liste der Bereiche: **Meldungen, Zuhause, Hydra, Aufgaben, Wartet auf Till, Rechner, Mining**. Je Bereich ein
  Schalter an/aus und Pfeile hoch/runter für die Reihenfolge. Uhr/Datum oben und „Zurück zum Video“ unten sind fest.
- Einstellungen je Bereich (nur diese, keine freien Texte):

| Bereich | Einstellung | Standard |
|---|---|---|
| Meldungen | höchstens n unter „Neu“ voll anzeigen (1–5) | **3** |
| Zuhause | Räume: alle oder eine Auswahl (Haken je Raum, aus den Favoriten) | alle |
| Aufgaben | Aufgaben von (Nutzer) | `till` (wie S2) |
| Wartet auf Till | Projekt mit GitHub-Zugang, Repos | wie S2 |
| Mining | eigener Bereich oder **in der Zeile „Rechner“** | **in „Rechner“** |

- Standard-Reihenfolge: Meldungen, Zuhause, Hydra, Aufgaben, Wartet auf Till, Rechner (mit Mining).
- **Speichern wirkt sofort**: Die Seite am Gehäuse holt ihre Anordnung mit den Daten (`/data` bekommt `layout`) und baut
  sich danach auf. Keine eigene Vorschau im Cockpit.
- Prüfung im Server und im Browser (eine Regel): bekannte Bereichs-IDs, jede höchstens einmal, Grenzen wie oben.
  Unbekannte oder alte Einträge → Standard. Alte `config.json` (S2: nur `tasks_user`, `github_project`, `github_repos`)
  bleibt gültig und wird ergänzt.

### Nie zu voll
- Passt nicht alles auf 1920 px, blendet die Seite **von unten** ganze Bereiche aus und zeigt klein
  „n Bereiche ausgeblendet (zu voll)“ über „Zurück“. Nichts wird abgeschnitten oder überlappt.
- Messung im Headless-Browser bei 1080×1920 mit vollen Daten (5 Meldungen, 4 Räume, 5 PRs, 5 Aufgaben) gehört zur Abnahme.

### Bewusst nicht in S4
- Kein freier Layout-Editor (Ziehen, Größen, Spalten), keine frei eingegebenen Texte oder HTML auf der Seite.
- Kein Schalten in Home Assistant (kommt erst mit „Knöpfe mit PIN“).
- Keine eigene Favoritenliste in der Vitrine: Die Auswahl passiert über die Räume, die Favoriten selbst pflegt Till im
  HA-Modul.

### Abnahme S4 (19.10.2026, vitrine 0.10.0)
- Till: „klappt“ – Zuhause stimmt, Bereiche im Cockpit ausgeschaltet (15:12 gespeichert: Aufgaben und
  „Wartet auf Till“ aus), am Gehäuse übernommen.
- Gemessen auf .2: Zuhause mit 4 Räumen (Wohnzimmer 22,4 °C/53 %, Küche 23,1 °C/52 %, Schlafzimmer 22,1 °C/55 %,
  Alex Zimmer grau „seit 13 h“); `/data` liefert das gespeicherte `layout`; 0 × `flip_done`; Firefox 0,8 % eines Kerns.
- Reihenfolge der Räume = Reihenfolge der Favoriten im HA-Modul (erster Favorit eines Raums zählt). Alex Zimmer steht vor
  Küche, weil die Steckdose dort Favorit Nr. 4 ist – zum Umsortieren die Favoriten im HA-Modul ordnen.

### Akzeptanz S4
- Zuhause zeigt die Räume mit echten Werten von .2 (Abgleich mit HA). Alex Zimmer grau mit „nicht erreichbar seit …“.
- Bereich im Cockpit ausschalten oder verschieben → binnen 10 s am Gehäuse so zu sehen.
- Ohne HA-Modul oder ohne Favoriten-Tabelle → Zuhause `null`, Rest unverändert (Tests).
- Ungültige Einstellungen werden abgelehnt (Server und Browser), alte Config bleibt gültig (Tests).
- Volle Seite: nichts läuft über 1920 px, der Hinweis „ausgeblendet“ erscheint (Headless-Test). Firefox < 5 % eines Kerns.

### Entscheidungen S4 (Till, 19.10.2026)
1. Zuhause = Option A, nur anzeigen, mit Tills HA-Favoriten.
2. Aufgeräumt: eine Zeile je Raum, Batterie nur bei wenig Ladung, nicht erreichbar grau.
3. Einstellungsseite statt fester Anordnung, ohne freien Editor. Voreinstellungen: Mining in „Rechner“, höchstens 3
   Meldungen unter „Neu“.

## S5 — Seiten (Entscheidung Till 19.10.2026: Option B, feste Seiten; abgenommen am Gehäuse am 19.10.2026, vitrine 0.11.0)

S4 ist abgenommen. Bisher blendet die Statuszentrale bei Platzmangel ganze Bereiche aus. S5 verteilt die Bereiche auf
**feste Seiten**, die Till im Cockpit zuordnet. Unten sitzen Knubbel zum Blättern. Weiterhin nur lesen: Blättern ändert
nichts am Server.

### Seiten
- Jeder Bereich bekommt eine **Seite 1–3** (Einstellung `pages`, Bereich → Seite). An/aus und Reihenfolge bleiben; die
  Reihenfolge gilt innerhalb der Seite.
- Voreinstellung: **Seite 1** Meldungen, Zuhause, Hydra · **Seite 2** Aufgaben, Wartet auf Till, Rechner, Mining.
- Belegt sind nur Seiten mit mindestens einem eingeschalteten Bereich, der Daten hat. Leere Seiten gibt es nicht;
  ist die gewählte Seite leer geworden, zeigt die Seite die nächste belegte.
- „Nie zu voll“ gilt **je Seite** (wie S4): Passt eine Seite nicht, werden dort ganze Bereiche von unten ausgeblendet,
  mit Hinweis.
- Alte Einstellung ohne `pages` → Voreinstellung.

### Knubbel
- Unten zwischen „Stand“ und „Zurück zum Video“: ein Knubbel je belegter Seite (● aktuelle, ○ andere), groß genug fürs
  Trackpad (mindestens 64 px Klickfläche). Nur sichtbar, wenn mehr als eine Seite belegt ist.
- Klick auf einen Knubbel wechselt sofort die Seite (im Browser, ohne Anfrage an den Server).
- **Nie automatisch blättern.**
- **Zurück auf Seite 1**, wenn so lange keine Maus-/Klick-Eingabe kam wie die Rückkehrzeit zum Video
  (`dashboard_return_seconds`, wird mit `layout` geliefert). So beginnt die Statuszentrale nach jedem Video wieder vorn.

### Cockpit
- In „Statuszentrale anpassen“ je Bereich eine Auswahl „Seite 1 / 2 / 3“. Die Liste zeigt die Bereiche nach Seite
  gruppiert (Überschrift „Seite 1“ …), die Pfeile verschieben innerhalb der Gesamtreihenfolge.
- Prüfung im Server und Browser (eine Regel wie S4): Schlüssel nur bekannte Bereiche, Werte 1–3.

### Akzeptanz S5
- Voreinstellung: Seite 1 Meldungen/Zuhause/Hydra, Knubbel ● ○ unten; Klick → Seite 2 mit Rechner (+ Mining).
- Im Cockpit einen Bereich auf Seite 3 legen → binnen 10 s drei Knubbel am Gehäuse.
- 2 min ohne Eingabe → Video; nächste Mausbewegung → Statuszentrale auf Seite 1.
- Ungültige Seitenzuordnung wird abgelehnt (Server und Browser), alte Config bleibt gültig (Tests).
- Seite blättert nicht von selbst (Test). Firefox < 5 % eines Kerns.

### Abnahme S5 (19.10.2026, vitrine 0.11.0)
- Till: Rechner und Mining im Cockpit auf Seite 3 gelegt → drei Knubbel; Klick auf den dritten zeigt Rechner + Mining;
  nach dem Video startet die Statuszentrale wieder auf Seite 1. „Beides passt.“
- Gemessen auf .2: `layout.pages` kommt an (machine/mining = 3), `return_seconds` 120, 0 Fehler, 0 × `flip_done`.

### Bewusst nicht in S5
- Kein automatisches Blättern, keine Wischgesten (kein Touch), keine Seitennamen.

## S6 — Chat am Gehäuse (Entscheidungen Till 19.10.2026)

Am Gehäuse mit Hydra schreiben: Eingabe über eine Bluetooth-Tastatur (Koppeln: eigener Task), Antwort am Display.
Till hat **Option B** gewählt: Chat mit dem **vollen Buddy** (alle Werkzeuge), weil im Haushalt nur 2 Personen sind.

### Ausgangslage (Code 19.10. geprüft)
- Der Kern hat den Weg schon: `hydrahive.communication.router.handle_incoming(IncomingEvent)`, genutzt von Discord,
  WhatsApp und Mail. Erst der Butler, dann der Buddy (`primary_agent_for`). Je `(agent, channel, external_user_id)` eine
  **dauerhafte Session** (`_session_lookup.find_or_create`). Die Antwort wird vor der Rückgabe mit den Secrets des
  Besitzers **geschwärzt**. Läuft die Session schon → `SessionAlreadyRunning`.
- Openbox im Kiosk ist abgesichert (0.11.2): kein Menü, kein Terminal, keine Tastenkürzel.

### Seite „Chat“
- **Eigene Seite** mit eigenem Knubbel (immer ganz rechts, Zeichen „💬“ nur wenn die Schrift es kann, sonst „Chat“).
  Nicht Teil der Seitenzuordnung 1–3. Im Cockpit an/aus (`chat_enabled`, Standard an).
- Aufbau hochkant: Verlauf oben (die letzten 20 Beiträge, neueste unten, scrollt mit), Eingabezeile unten über „Zurück“.
- **Tippen holt den Chat:** Eine Buchstaben-/Zahlentaste auf einer anderen Seite wechselt zur Chat-Seite, der Buchstabe
  landet im Feld. Enter schickt ab, Escape leert das Feld.
- Während Hydra antwortet: „Hydra denkt …“, Eingabe gesperrt. Fehler → rote Zeile (z. B. „Hydra antwortet noch“).
- Antwort **am Stück** (sobald fertig). Darstellung als **reiner Text** (Absätze, Listen als Zeilen), nur `textContent`.
  Streaming (Wort für Wort) kommt später als eigene Etappe.

### Weg der Nachricht
- `POST /api/module-device/vitrine/chat?k=…` (Kiosk-Schlüssel + localhost wie S1–S5, Rate-Limit des Kerns).
  Körper nur `{"text": "…"}`, 1–2000 Zeichen nach Trimmen, sonst 422. Ruft
  `handle_incoming(IncomingEvent(channel="vitrine", external_user_id="gehaeuse", target_username=<Besitzer>,
  sender_name="Gehäuse", text=…))`. Antwort `{"reply": "…"}` (gekürzt auf 8000 Zeichen).
  Läuft der Chat schon → 409 `{"code": "busy"}`. Kein Agent/Fehler → 503 `{"code": "unavailable"}`.
- `GET /api/module-device/vitrine/chat?k=…` → die letzten 20 Beiträge der Gehäuse-Session (nur Rolle user/assistant
  und deren Text, keine Werkzeug-Aufrufe, geschwärzt und gekürzt wie oben). Fehlt die Session → leere Liste.
- **Eigene Session** „Gehäuse“ (Till, 19.10.): getrennt von Tills Cockpit-Chat. Besitzer = `tasks_user` (Standard `till`).
- Kanal `vitrine` erscheint in HydraHive wie andere Kanäle (Session-Titel „vitrine: Gehäuse“).

### Rückkehr zum Video
- Wie bisher nach 2 min ohne Eingabe (Till, 19.10.). Tippen zählt als Eingabe (X-Leerlauf).
- **Während Hydra antwortet** zählt die Zeit nicht: Das Backend legt für die Dauer des Aufrufs `chat_busy` (mit Zeitstempel)
  in den Datenordner; der Dienst bleibt im Dashboard, solange die Datei frisch ist (höchstens 10 min, dann gilt sie als
  verwaist). Danach beginnen die 2 min neu.

### Sicherheit
- Erste Kiosk-Route, die einen **Agenten mit allen Werkzeugen** startet – bewusst so entschieden (2 Personen, Option B).
- Schutz bleibt: Kiosk-Schlüssel + direkte Verbindung von 127.0.0.1, Rate-Limit, Openbox ohne Menü, Firefox nur 127.0.0.1.
- Ausgabe vom Kern geschwärzt, Länge begrenzt. Keine Dateien, keine Bilder, keine Links zum Anklicken.
- Später (eigene Etappe „Knöpfe mit PIN“): optional PIN vor dem Chat.

### Akzeptanz S6
- Tastatur gekoppelt → auf Seite 1 tippen → Chat-Seite mit dem Buchstaben im Feld; Enter → „Hydra denkt …“ → Antwort.
- Session „vitrine: Gehäuse“ ist getrennt von Tills Cockpit-Chat; nach Neustart des Dienstes ist der Verlauf noch da.
- Lange Antwort (> 2 min Denkzeit) → kein Zurück zum Video währenddessen; danach 2 min Ruhe → Video.
- Route: ohne/falscher Schlüssel, andere Adresse → 404; leerer/zu langer Text → 422; zweite Nachricht während einer
  laufenden → 409 (Tests). Secret in der Antwort erscheint geschwärzt (Test).
- Seite ohne `innerHTML`; Firefox < 5 % eines Kerns im Leerlauf.

### Bewusst nicht in S6
- Streaming (folgt), Sprache (später über das Voice-Modul), Bilder/Dateien, mehrere Gespräche, PIN.

### Entscheidungen S6 (Till, 19.10.2026)
1. Option B: voller Buddy am Gehäuse.
2. Eigene Seite „Chat“ mit eigenem Knubbel.
3. Eigene Session „Gehäuse“, getrennt vom Cockpit-Chat.
4. Antwort zuerst am Stück; Streaming als spätere Etappe.
5. Zurück zum Video nach 2 min ohne Eingabe; nicht während Hydra antwortet.

## S7 — Bluetooth-Geräte koppeln (Till 21.10.2026: „an beide Stellen“, Kiosk und Cockpit)

Am 21.10. hat das Koppeln der Rapoo-Tastatur (E9300G) von Hand über eine Stunde gedauert. S7 macht daraus einen Knopf, an
**beiden Stellen**: auf dem Gehäuse-Display (Kiosk) und in der Vitrine-Seite im Cockpit.

### Ausgangslage (am 21.10. auf .2 gemessen)
- Adapter Realtek RTL8922AE (`hci0`, USB-Teil `0bda:8922`), BlueZ 5.85. **Ohne Antennen** kamen Geräte mit −98 … −106 dBm
  an und Verbindungen brachen nach 420 ms ab (btmon: `Connection Failed to be Established`). Mit Antenne: −56 dBm.
- Der Dienst-Nutzer `hydrahive` darf BlueZ über D-Bus steuern (Default-Policy; `pairable on/off` als `hydrahive` geprüft).
  Es gibt keine D-Bus-Bibliothek im Kern; `busctl` (systemd) ist vorhanden.
- **Multi-Mode-Tastaturen** melden sich mit zwei Adressen und Namen (Rapoo: `RAPOO BT3.0 KB` klassisch,
  `RAPOO BT4.0 KB` LE). Die LE-Kopplung brach mit `auth failed 0x05` ab, die klassische klappte sofort.
- Der Adapter stand auf nicht „bondable“; Kopplungen ohne Bonding verfallen (`AuthenticationCanceled`).

### Was der Knopf tut
- **„Gerät koppeln“** öffnet das Kopplungsfenster für **2 Minuten**: Adapter an, bondable, pairable, Suche (klassisch + LE).
  Danach schließt es sich von selbst (Suche aus, pairable aus). Ein zweiter Druck verlängert nicht, er zeigt die Restzeit.
- **Liste** (alle 2 s aktuell): Name (sonst „Unbekanntes Gerät“), Art aus dem Icon (Tastatur, Maus, Kopfhörer, Lautsprecher,
  Telefon, Sonstiges), **Signal** als Balken mit dBm, Zustand (neu / gekoppelt / verbunden). Ohne Namen und schwächer als
  −90 dBm erst unter „Weitere Geräte“ (zugeklappt).
- **Tippen auf ein Gerät koppelt es:** pair → trust → connect. Fordert das Gerät einen **Code**, erscheint er **groß** mit dem
  Satz „Auf der Tastatur eintippen, dann Enter“. Fragt das Gerät nach Bestätigung (Zahlenvergleich), wird bestätigt –
  das Tippen auf das Gerät ist die Bestätigung.
- **Zwei Adressen, ein Gerät:** Gleicher Name bis auf `BT3.0`/`BT4.0`/`LE` und gleiche Hersteller-Kennung (erste drei
  Bytes der Adresse) → eine Zeile. Gekoppelt wird **zuerst die klassische** Adresse, bei Fehler die LE-Adresse.
- **Gekoppelte Geräte** (immer sichtbar, auch ohne offenes Fenster): Name, verbunden ja/nein, Knopf **„Entfernen“**
  (nur Cockpit; am Kiosk nur ansehen, damit niemand im Vorbeigehen die Tastatur entkoppelt).
- **Signal-Hinweis:** Ist das stärkste Gerät in der Liste schwächer als −85 dBm, steht oben „Sehr schwacher Empfang –
  Antennen am Rechner prüfen“.

### Kiosk
- Neuer Knubbel **„Bluetooth“** (ganz rechts, vor „Chat“), eigene Seite wie der Chat; nicht Teil der Seitenzuordnung 1–3.
  Im Cockpit an/aus (`bluetooth_enabled`, Standard an).
- Während das Kopplungsfenster offen ist, zählt die Rückkehr zum Video **nicht** (wie `chat_busy`, Datei
  `bt_busy`, verwaist nach 3 min).
- Bedienung mit Maus/Trackpad (kein Touch): Zeilen mindestens 64 px hoch.

### Cockpit
- Karte **„Bluetooth“** auf der Vitrine-Seite: dieselbe Liste + „Entfernen“, Adapter-Name und -Zustand, Hinweis bei
  schwachem Signal. Nur mit dem Recht `module.vitrine` (wie die übrige Vitrine-Seite).

### Weg (Backend + Dienst)
- **Der Vitrine-Dienst** (`hydrahive2-vitrine`, läuft als `hydrahive`) übernimmt Bluetooth. Grund: Ein Kopplungs-Agent
  (`org.bluez.Agent1`, Fähigkeit `KeyboardDisplay`) muss als D-Bus-Objekt **dauerhaft** erreichbar sein, solange das
  Fenster offen ist. Das kann ein Dienst, aber kein einzelner HTTP-Aufruf. Neues Paket `dbus-fast` in der venv des Dienstes
  (asynchron, reines Python; auf .2 per pip verfügbar geprüft). Der Kern bekommt **keine** neue Abhängigkeit.
- Weg wie bei allem anderen der Vitrine (SPEC §1: „spricht nur lokal über Dateien“): Das Backend schreibt Aufträge nach
  `inbox/bt-*.json` (`scan`, `pair <Adresse>`, `remove <Adresse>`), der Dienst schreibt den Stand nach `bluetooth.json`
  (Adapter, Fenster offen bis, Geräte, laufende Kopplung, angezeigter Code, letzter Fehler). Kein Socket, kein Port.
- Routen, Kiosk: `GET /bluetooth`, `POST /bluetooth/scan`, `POST /bluetooth/pair` unter
  `/api/module-device/vitrine/…?k=…` (Kiosk-Schlüssel + 127.0.0.1 wie S1–S6).
  Cockpit: dieselben unter `/api/modules/vitrine/…` plus `DELETE /bluetooth/{adresse}`, mit Login + Recht.
- Der Dienst setzt beim Öffnen `Powered`, `Pairable`, `Discoverable` (180 s Grenze von BlueZ, wir schließen nach 120 s),
  bondable über `Pairable` (BlueZ setzt Bonding mit). Beim Schließen und beim Start des Dienstes: `Pairable` und
  `Discoverable` aus, Suche aus, Agent abmelden.
- **Eingaben:** Adresse nur im Format `XX:XX:XX:XX:XX:XX` (Hex, Großbuchstaben), sonst 422. Koppeln nur bei offenem
  Fenster und nur für Geräte, die die laufende Suche gesehen hat (sonst 409 `window_closed` bzw. `not_seen`). Keine
  Freitext-Felder; Aufträge sind feste Arten mit geprüfter Adresse.
- Ausgaben: nur Name (gekürzt 60), Art, Signal, Zustand, Adresse. Keine Schlüssel, keine UUID-Listen.

### Sicherheit
- Koppeln ist mächtig: Eine gekoppelte Tastatur kann am Server tippen. Deshalb: Fenster **nur auf Knopfdruck**, **2 min**,
  danach zu; Koppeln **nur nach Tippen** auf ein Gerät; außerhalb des Fensters ist der Adapter nicht pairable und nicht
  discoverable (der Server ist nie für andere sichtbar).
- Kiosk: Kiosk-Schlüssel + direkte Verbindung von 127.0.0.1 + Rate-Limit des Kerns; „Entfernen“ gibt es am Kiosk nicht.
- Jede Kopplung und jedes Entfernen kommt als Meldung in den Verlauf (S3): „Bluetooth: <Name> gekoppelt“.

### Akzeptanz S7
- Knopf „Gerät koppeln“ → binnen 5 s erscheint die Rapoo (beide Adressen als **eine** Zeile) mit Signalbalken.
- Tippen → gekoppelt, vertraut, verbunden; nach Neustart von .2 verbindet sie sich von selbst wieder.
- Nach 2 min: `Pairable: no`, `Discoverable: no`, Suche aus (geprüft mit `bluetoothctl show`).
- Ungültige Adresse → 422; nicht gesehene Adresse → 409; Kiosk ohne/mit falschem Schlüssel oder von anderer Adresse → 404;
  Cockpit ohne Recht → 403 (Tests).
- Am Kiosk gibt es kein „Entfernen“ (Test). Seite ohne `innerHTML`.

### Bewusst nicht in S7
- Audio-Geräte als Ausgang einstellen (PipeWire), Dateiübertragung, Geräte umbenennen, mehrere Adapter.

### Entscheidungen S7 (Till, 21.10.2026)
1. An beiden Stellen: Kiosk und Cockpit.
2. Fenster nur auf Knopfdruck, 2 min, Koppeln nur nach Tippen, danach zu.

## Bewusst nicht (V1 der Statuszentrale)

- keine Aktionen mit Folgen (Merge, Dienste, Update, Zonen, Schalter) – kommen später nur mit PIN
- kein Home Assistant, kein Chat, keine Sprache (eigene Etappen danach)
- kein voller Desktop, keine Fenster außer dem Kiosk-Browser
- kein Touch (das Display hat keinen)

## Sicherheit

- Kiosk-Schlüssel: nur Lesen, nur Dashboard-Route, nur localhost; wird bei jeder Installation neu erzeugt
- Der Kiosk-Nutzer kann sich nicht per SSH oder Passwort anmelden; der Browser darf nur `127.0.0.1` öffnen (Richtlinie im Browser)
- Wer im Wohnzimmer an der Maus ist, sieht Status, aber kann nichts auslösen außer „Gelesen“ und „Zurück“
- Installation fügt hinzu: `linux-modules-evdi-generic`, `libevdi1`, Openbox, Browser, Kiosk-Nutzer, sddm-Autologin. Deinstallation entfernt Nutzer und Autologin

## Etappen

1. **S1 Umschalten:** EVDI-Quelle im Dienst, Kiosk-Sitzung, Leerlauf-Abfrage, 2-min-Rückkehr, Platzhalter-Seite. Abnahme am Gehäuse
2. **S2 Statuszentrale:** Daten-Route mit Kiosk-Schlüssel, Dashboard-Seite, Cockpit-Einstellung Rückkehrzeit
3. **S3 Meldungen:** Hinweis auf den Karten, Neu + Verlauf (24 h) in der Statuszentrale, Knopf „Gelesen“ (Details: Abschnitt S3)
4. **S4 Zuhause + Anordnung:** HA-Favoriten je Raum, Einstellungsseite (an/aus, Reihenfolge, Einstellungen je Bereich)
5. **S5 Seiten:** Bereiche fest auf Seiten 1–3, Knubbel unten zum Blättern
6. **S6 Chat:** eigene Seite, BT-Tastatur, voller Buddy in eigener Session, Antwort am Stück
7. **S7 Bluetooth:** Geräte suchen und koppeln, am Kiosk und im Cockpit
8. danach: Streaming im Chat, Sprache, Knöpfe mit PIN

## Akzeptanzkriterien

- Maus bewegen → Dashboard binnen 1 s; 2 min nichts → zurück zum Video; Knopf „Zurück“ → sofort
- Im Video-Modus bleibt die Last wie heute (< 10 % eines Kerns); Dashboard ohne Bewegung < 5 %, mit Bewegung < 20 % (gemessen über 60 s)
- Nie ist der sddm-Anmeldebildschirm oder ein Benutzername auf dem Display zu sehen (auch nicht beim Hochfahren)
- Nach einem Neustart von .2: binnen 90 s Video; Maus funktioniert wie oben
- Browser abgestürzt oder EVDI fehlt → Video läuft weiter, das Cockpit zeigt „Dashboard nicht verfügbar“
- Die Daten-Route lehnt ohne Schlüssel, mit falschem Schlüssel und von einer anderen Adresse als 127.0.0.1 ab (Tests)

## Entscheidungen (Till, 18.10.2026)

1. Der sddm-Anmeldebildschirm auf .2 wird durch die Kiosk-Sitzung **ersetzt**.
2. Zurück zum Video nach **2 Minuten** ohne Eingabe, im Cockpit änderbar.
3. Nachts weckt die Maus das Dashboard **immer**. Nach der Rückkehrzeit wird es wieder dunkel.
4. Browser: **zuerst Firefox** (schon installiert) und die Last messen. Chromium nur, wenn das Kriterium (< 20 %) nicht erreicht wird.
