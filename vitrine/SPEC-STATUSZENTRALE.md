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
3. **S3 Meldungen:** Hinweis auf den Karten, Volltext oben, Knopf „Gelesen“
4. danach (eigene Specs): Home Assistant, Chat/Sprache, Knöpfe mit PIN

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
