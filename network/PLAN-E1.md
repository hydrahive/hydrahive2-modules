# Modul „Netzwerk“ – Bauplan Etappe 1 (nur lesen)

Stand 01.11.2026 · Task d2b126e4 · Auslöser: Störung am Vodafone-Kabelanschluss seit dem 27.10. (Glasfaserdefekt
in Frankfurt), Ticket gestellt. Ziel: lückenlose, belegte Daten für den Anbieter, ohne Terminal, alles im Cockpit.

## 1. Ausgangslage (gemessen am 01.11., nur lesend)

| Gerät | Adresse | Zugang | Ergebnis |
|---|---|---|---|
| UniFi Dream Machine Pro (Network 10.6.109, FW 5.1.34) | 192.168.178.1 | API-Schlüssel im Header `X-API-KEY` (nicht `Bearer`) | lesbar: Integration-API v1, `stat/health`, `stat/sysinfo`, `stat/report/*`, `archive.speedtest`, v2 `system-log/all`, `aggregated-dashboard`, `wan/enriched-configuration` |
| FRITZ!Box 6591 Cable (Vodafone), FRITZ!OS 8.25 | 192.168.3.1 | TR-064 Port 49000 antwortet, Nutzer fehlt noch | Kabelwerte (DOCSIS) und Ereignisprotokoll erst mit eigenem Nutzer |

Kette: HydraHive-Server → Dream Machine → FRITZ!Box (Kabelmodem, doppeltes NAT) → Vodafone (AS3209).

Befund aus der Dream Machine (Schnappschuss `_work/netz-beweise/udm-20261101-2147.json.gz`, sha256 `0a34c66a…`):
- Ausfälle von „Internet 1“ am 27.10. ab 14:17 (8 h 31 min), am 28.10. mehrfach (7 h 22 min, 1 h 14 min, 1 h 23 min …),
  am 29.10. 3 h 27 min, ab dem 30.10. viele kurze Aussetzer, am 01.11. sechs Ausfälle.
- Geschwindigkeitstests: 25.10. 947/51 Mbit, am 01.11. 364/3, 563/3, 122/0, 270/2 Mbit. Gebucht sind 1000/50.
  **Der Upload ist auf 0 bis 3 Mbit eingebrochen.**
- Die Dream Machine löscht ihre 5-Minuten-Werte nach 24 Stunden, die Stundenwerte nach 7 Tagen und die Tageswerte
  nach 90 Tagen. Ohne eigenen Speicher gehen Beweise verloren.
- **Ausweichweg:** Am 27.10. hing ein Mobilfunk-Stick als Fallback per USB an der FRITZ!Box, seit dem 30.10. ein
  MiFi-Router von Vodafone. Die FRITZ!Box schaltet selbst um, deshalb sieht die Dream Machine bei totem Kabel oft
  „Internet da“. Die Stundenwerte zeigen drei Muster: **kein Internet** (Antwortzeit 0, kaum Verkehr), z. B. 27.10.
  15–21 Uhr, 28.10. 02–08 Uhr, 29.10. 01–02 Uhr; **vermutlich Mobilfunk** (kürzeste Antwortzeit ≥ 18 ms statt 7–9 ms),
  z. B. 28.10. 11, 15, 19 Uhr und 31.10. 02–03 Uhr; **kabeltypisch** (7–9 ms), z. B. 29.10. ab 04 Uhr. Das ist ein
  Hinweis, kein Beweis. Für den Weg (Kabel/Mobilfunk) ist das Ereignisprotokoll der FRITZ!Box die entscheidende
  Quelle. Es fasst nur eine begrenzte Zahl Einträge, darum muss es bald gesichert werden.

## 2. Rechtlicher Rahmen (Quelle: gesetze-im-internet.de, gelesen am 01.11.)

- **§ 58 Abs. 3 TKG (Entschädigung):** Ist die Störung nicht innerhalb von zwei Kalendertagen nach der Störungsmeldung
  beseitigt, gibt es für jeden Tag des **vollständigen Ausfalls** eine Entschädigung. Am 3. und 4. Tag 5 € oder 10 %,
  ab dem 5. Tag 10 € oder 20 % des Monatspreises, je nachdem, was höher ist. Eine Minderung wird angerechnet.
  Ausnahme: höhere Gewalt. Ob ein Glasfaserdefekt darunter fällt, entscheidet nicht das Modul.
- **§ 57 Abs. 4 TKG (Minderung bei zu wenig Geschwindigkeit):** zählt nur mit einer von der Bundesnetzagentur
  bereitgestellten oder zertifizierten Messung (breitbandmessung.de). Das Modul ersetzt sie nicht. Es zeigt aber, wann
  und wie oft gemessen werden sollte, und hält eine Liste der Messungen. Den genauen Ablauf der Messkampagne prüfe ich
  vor dem Bau des Berichts noch einmal auf der Seite der Bundesnetzagentur.
- Im Bericht steht deshalb: „Eigene Messung, keine Rechtsberatung.“ Er enthält Rohdaten mit Prüfsumme.

## 3. Umfang Etappe 1

### 3a – Grundgerüst, Zugänge, Sammler, Speicher (zuerst, damit sofort gesammelt wird)
- Neues Modul `network` („Netzwerk“), Bereich `zuhause`, Rechte: `module.network` (ansehen) und
  `network.configure` (Zugänge und Tarif), beide `admin_only`.
- **Einstellungen im Modul:** Adresse und API-Schlüssel der Dream Machine, Adresse, Nutzer und Passwort der FRITZ!Box,
  Tarif (herunter/hoch, Monatspreis), Störungsmeldungen (Datum, Ticketnummer, Notiz).
  Geheimnisse verschlüsselt wie in `telephony/backend/secrets.py` (AES-GCM, Schlüssel aus dem Kern, AAD je Feld).
  Sie werden nie ausgegeben, nach außen geht nur „gesetzt“.
- **Zertifikat der Dream Machine:** Das Zertifikat ist selbst ausgestellt. Beim ersten Kontakt wird der Fingerabdruck
  angezeigt und bestätigt, danach gilt er fest (Pinning). Bei einer Abweichung erscheint ein klarer Fehler, die
  Verbindung wird nicht stillschweigend angenommen.
- Verbindungen nur zu den eingetragenen Heimnetz-Adressen.
- **Sammler** über `ctx.register_job`:
  - **jede Minute, eigene Messung:** Ping zur Dream Machine, zur FRITZ!Box, zum ersten Vodafone-Knoten (stündlich per
    `tracepath` ermittelt) und zu zwei Zielen im Internet (1.1.1.1, 9.9.9.9). Dazu eine Namensauflösung und ein
    HTTPS-Aufbau. Werte: Verlust, Antwortzeit, Schwankung. Ping läuft ohne root mit fester Argumentliste.
  - **alle 5 Minuten:** Dream Machine `stat/health` (Status „Internet 1“, Aussetzer, letzter Speedtest) und
    `5minutes.site`/`5minutes.gw`. Von der FRITZ!Box: Kabelstatus und Kabelwerte je Kanal (Pegel, Signalqualität,
    korrigierbare und nicht korrigierbare Fehler) über `data.lua?page=docInfo`, Anmeldung über
    `login_sid.lua?version=2` (PBKDF2). Dazu Synchronstatus über TR-064.
  - **stündlich:** Ereignisprotokoll der Dream Machine (doppelte Einträge über die `id` ausgeschlossen),
    Speedtest-Archiv, `hourly.*`. Ereignisprotokoll der FRITZ!Box (TR-064 `GetDeviceLog`), ebenfalls ohne Dubletten.
- **Weg erkennen (Kabel oder Mobilfunk):** jede Minute aus (1) dem Status der FRITZ!Box (Kabel synchron?
  Mobilfunk-Fallback aktiv?), (2) dem ersten Vodafone-Knoten hinter der FRITZ!Box (heute 81.210.132.146 = Kabelnetz)
  und (3) der kürzesten Antwortzeit. Jede Messung bekommt den Weg „Kabel“, „Mobilfunk“, „keins“ oder „unklar“.
  Störungen werden getrennt gezählt: **Kabel aus** (das zählt gegenüber dem Anbieter) und **Internet ganz aus**.
  Für die Vorgeschichte ab dem 25.10. nur als „vermutlich“ markiert, solange die FRITZ!Box es nicht belegt.
- **Speicher:** eigene SQLite-Datenbank (Migration `001_init.sql`). Minutenwerte 90 Tage, danach als Stundenmittel
  2 Jahre. Ereignisse, Speedtests und Störungen dauerhaft. Aufräumen nur der eigenen Zeilen (`only_own_rows`).
- **Einmal-Import:** Den Schnappschuss vom 01.11. übernehme ich als Vorgeschichte ab dem 25.10. Jede Zeile bekommt
  eine Quellenangabe.

### 3b – Oberfläche
- **Übersicht:** Ampel je Abschnitt (Zuhause, FRITZ!Box/Kabel, Vodafone, Internet), Diagramm der letzten 24 Stunden
  (Antwortzeit, Verlust, Ausfälle), Geschwindigkeit gegenüber dem Tarif.
- **Störungen:** Liste mit Beginn, Ende, Dauer, betroffenem Abschnitt und Quelle (eigene Messung, Dream Machine,
  FRITZ!Box). Tage mit vollständigem Ausfall sind markiert. Ein Tag lässt sich von Hand als „vollständig ausgefallen“
  bestätigen, mit Begründung, z. B. „Kabel tot, Mobilfunk-Backup“. Störungsmeldung und Ticket kann man eintragen.
- **Leitung:** Verlauf der Kabelwerte, Kanäle mit Fehlern hervorgehoben.
- **Geräte:** Geräte und Clients der Dream Machine, nur Anzeige.
- Breiten 1600, 1280, 393 und 375 px. Farben nur aus dem Kern. Deutsch und Englisch.

### 3c – Störungsbericht
- Zeitraum wählen. Daraus wird eine druckbare Seite (Browser → PDF) plus Export als CSV und JSON mit Prüfsumme.
- Inhalt: Anschluss und Tarif, Zusammenfassung, Tage mit vollständigem Ausfall, Rechnung nach § 58 (nur wenn eine
  Störungsmeldung eingetragen ist, mit Rechenweg), Geschwindigkeit gegenüber dem Tarif (Upload getrennt),
  Auffälligkeiten der Kabelwerte, Ereignisliste, Hinweis auf die Messung der Bundesnetzagentur.
- **Agenten-Werkzeuge (nur lesen):** `network_status` und `network_outages`. Damit kann z. B. Buddy beantworten:
  „Wie war mein Internet diese Woche?“

## 4. Nicht in Etappe 1
- Konfiguration ändern (Etappe 2, jeweils mit Bestätigung): Geräte neu starten, Speedtest auslösen, Clients sperren,
  Portfreigaben, WLAN.
- Benachrichtigung bei Ausfall bzw. Wiederkehr (Mail/Discord) als mögliche Etappe 1d.
- Eigener Upload-/Download-Test, der Datenvolumen verbraucht. Zunächst gelten die Speedtests der Dream Machine.

## 5. Prüfung
- Rote Tests zuerst. Netzaufrufe in Tests immer gemockt, Antworten aus dem echten Schnappschuss als Testdaten
  (ohne Schlüssel, MAC-Adressen gekürzt).
- Mutanten in Backend und Frontend. Volle Reihe (pytest `-n 16`, vitest, tsc, eslint, ruff), `check_version_bump`,
  `check_test_safety`, `scripts/tests`.
- hydratest: Modul mit echtem Zugang zur Dream Machine bzw. FRITZ!Box, nur lesend. Danach E2E über sichtbare Texte.
- Eintrag in `hub.json`, `NAV_AREA.de.md` und `scripts/tests/test_nav_area.py`. `_hh_isolation.py` unverändert kopieren.

## 6. Offene Fragen an Till
1. Erledigt: Fallback per USB-Stick an der FRITZ!Box, seit dem 30.10. MiFi-Router von Vodafone.
   Offen: Hängt der MiFi per USB oder per LAN/WLAN an der FRITZ!Box?
2. Monatspreis, Datum der Störungsmeldung und Ticketnummer. Das trägst du später selbst im Modul ein.
3. FRITZ!Box-Nutzer anlegen: System → FRITZ!Box-Benutzer, nur „FRITZ!Box Einstellungen“ ansehen, ohne
   Internetzugriff. Hinterlegen wie den UniFi-Schlüssel. **Eilig**, weil das Ereignisprotokoll der FRITZ!Box die
   Tage ab dem 27.10. nur begrenzt aufbewahrt.
4. Sollen die automatischen Speedtests der Dream Machine dichter laufen? Das stellst du in der Dream Machine ein; ein
   Test bei 1 Gbit verbraucht rund 1 GB.
