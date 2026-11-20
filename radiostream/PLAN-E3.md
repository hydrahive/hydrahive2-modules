# Radiostream – Bauplan Etappe 3 (Live-Studio)

> Wunsch Till (31.10.2026): Etappe 3. Alle Wege einbauen, die gemischte Arbeitsplätze brauchen: eigenes Sendeprogramm
> **und** Mikrofon im Browser, Jingles aus Upload **und** Bibliothek, Wünsche von Nutzern **und** Hörern.
> Moderieren dürfen auch Nicht-Admins mit eigenem Recht (Entscheidung B).

## Teilschritte (je eigene Version, eigener PR, eigene Probe)

| Schritt | Inhalt | Version |
|---|---|---|
| **3a** | Live über eigenes Sendeprogramm (BUTT, Mixxx, mAirList), Moderatoren-Zugänge, Reiter „Studio“, Musik leiser/aus, trennen | 0.3.0 |
| **3c** | Jingles (Upload oder Bibliotheksordner), Jingle-Tasten, Vorhören im Kopfhörer | 0.4.0 |
| **3b** | Mikrofon im Browser über HydraHive (eigene Anmeldung, kein offener Zugang) – **erst messen** | 0.5.0 |
| **3d** | Wunschliste: Nutzer in HydraHive, Hörer auf der Hörer-Seite (abschaltbar, standardmäßig aus), annehmen/ablehnen | 0.6.0 |

Reihenfolge 3a → 3c → 3b → 3d: 3a ist der stabilste Weg und sofort nutzbar. 3b ist der unsicherste (Browser-Ton,
Verzögerung) und wird vorher auf hydratest gemessen. 3d öffnet eine neue Tür nach außen und kommt zuletzt.
Je Schritt: Bauplan-Nachtrag hier, rote Tests, Code, Mutanten, Gegenprobe, volle Reihe, Probe hydratest, E2E 4 Breiten,
PR, Tills OK.

## Rechte (Entscheidung B, gilt für alle Schritte)

- Neues Recht im Manifest: `radiostream.moderate` – „Moderieren (Studio, Jingles, Wünsche)“, Standard `admin_only`.
  Admins geben es in den Freigaben an Nutzer oder Gruppen.
- Wer `radiostream.moderate` hat, braucht auch `module.radiostream` (Modul sehen). Studio-Schnittstellen prüfen beides.
- `radiostream.control` (Sender, Einstellungen, Quelle) bleibt getrennt und Admins vorbehalten, wie heute.
- **Moderatoren-Zugänge verwalten** (anlegen, Passwort neu, sperren, löschen) dürfen nur Inhaber von
  `radiostream.control`. Ein Moderator sieht nur seinen eigenen Zugang und kann sein Passwort neu erzeugen.
- Der Reiter „Studio“ erscheint nur mit `radiostream.moderate`.

## Schritt 3a – Live über eigenes Sendeprogramm

### Ablauf für den Moderator
1. Ein Admin legt im Reiter „Studio“ → „Zugänge“ einen Zugang für einen HydraHive-Nutzer an (der Nutzer muss
   `radiostream.moderate` haben). Das Passwort wird **einmal** angezeigt, mit Kopierknopf.
2. Die Seite zeigt die Einstellungen fürs Sendeprogramm: Server (Adresse dieses Servers), Port, Mount `/live`,
   Benutzer, Typ Icecast 2, Format MP3 oder Ogg. Dazu kurze Anleitungen für BUTT und Mixxx (Texte, keine Dateien).
3. Der Moderator verbindet sein Programm → im Studio steht „Live: <Name>“, die Musik wird je nach Wahl leiser oder aus.
4. Programm trennt oder Verbindung bricht ab → nach wenigen Sekunden läuft wieder der AutoDJ.

### Sender (Liquidsoap)
- `input.harbor("live", port=<live_port>, auth=…)` im Skript. Die Prüfung fragt das Modul über den vorhandenen
  Geräte-Weg (`/api/module-device/radiostream/feed/live-auth`, Feed-Schlüssel + 127.0.0.1): Benutzer + Passwort +
  Adresse. Das Modul vergleicht mit dem gespeicherten Hash (bcrypt) und prüft, ob der Nutzer noch existiert, das Recht
  `radiostream.moderate` noch hat und der Zugang nicht gesperrt ist. Nur ein Moderator gleichzeitig.
- Mischung: `live` über die Musik mit `smooth_add` (Musik leiser, Anteil einstellbar, Standard 20 %) oder per
  `fallback([live, programm])` (Musik aus). Umschalten über die Steuerdatei (`radio.sock`), ohne Neustart.
- Bei Verbindungsaufbau und -abbruch (`on_connect`/`on_disconnect`) meldet Liquidsoap an das Modul (Geräte-Weg) →
  Zustand „live seit … von …“ im Studio, Eintrag im Protokoll.
- „Trennen“ im Studio: `live.stop` über die Steuerdatei. Der Zugang wird zusätzlich für 60 s gesperrt (sonst wählt
  sich das Programm sofort wieder ein).
- „Jetzt läuft“ zeigt bei Live die Metadaten des Sendeprogramms (falls gesendet), sonst „Live: <Sendername>“.

### Netz
- Eigener Port, einstellbar im Reiter „Sender“ (Standard **8810**, nicht 8800/8001/8443, geprüft wie `listen_port`).
- Liquidsoap lauscht auf 0.0.0.0:<live_port>. Die Grenze setzt das Modul in der Prüfung: Jede Adresse außerhalb
  Heimnetz/Tailscale wird abgelehnt (dieselbe Liste wie bei der Hörer-Seite „home“). Zusätzlich
  `settings.harbor.max_connections` klein (4) und `timeout` kurz.
- **Offen bei Till:** Live aus dem Internet (Moderator unterwegs ohne Tailscale)? Vorschlag: nein, Tailscale nutzen.
  Ein späterer Schalter „Live auch aus dem Internet“ wäre möglich, dann nur über TLS.

### Daten (Migration `003_studio.sql`, additiv)
- `module_radiostream_hosts`: id, user_id, login (Benutzername fürs Programm), pw_hash, active, blocked_until,
  created_at/by, last_live_at.
- `module_radiostream_live_log`: id, host_id, started_at, ended_at, address (gekürzt auf das Netz), reason.
- `module_radiostream_station`: neue Spalten `live_port` (8810), `live_mode` (`duck`|`replace`), `duck_level` (0.2).

### Schnittstellen
- `GET  /studio` (moderate): Zustand (live ja/nein, wer, seit, Modus), eigene Verbindungsdaten.
- `POST /studio/mode` (moderate): `duck`|`replace`, Absenk-Anteil.
- `POST /studio/disconnect` (moderate): Live trennen.
- `GET/POST/DELETE /studio/hosts…` (control): Zugänge verwalten. `POST /studio/hosts/{id}/password` (control oder
  eigener Zugang): neues Passwort, einmal im Klartext zurück.
- Geräte-Weg (Feed-Schlüssel + 127.0.0.1): `POST /feed/live-auth`, `POST /feed/live-event`.

### Oberfläche
- Reiter **„Studio“**: Kasten „Live“ (Zustand, Knöpfe „Musik leiser“/„Musik aus“, Schieber Absenkung, „Trennen“),
  Kasten „So verbindest du dein Sendeprogramm“ (Daten + Anleitung BUTT/Mixxx), für Admins Kasten „Zugänge“.
- Reiter „Sender“: Feld „Live-Port“.
- Texte de/en, Fehler-Codes `radiostream_live_*` mit Text, Farben nur Farbstufen, eigene Dialoge (kein confirm).

### Prüfung 3a
- Rot zuerst: Inhalt des Liquidsoap-Skripts, Prüfung (Hash, Recht entzogen, gesperrt, fremde Adresse, zweiter
  Moderator, falsches Passwort mit Bremse), Rechte der Routen (Nutzer mit/ohne moderate, Admin), Protokoll.
- Skript mit Liquidsoap 2.2 **und** 2.4 prüfen (`liquidsoap --check`), wie bei 0.2.1.
- **Echt auf hydratest:** Ersatz fürs Sendeprogramm (`ffmpeg` → Icecast-Quelle an `:8810/live`) mit richtigem und
  falschem Passwort, aus dem Heimnetz und von (simuliert) fremder Adresse. Musik leiser/aus hörbar im Stream (Pegel
  messen), Trennen, Rückfall auf AutoDJ, Recht entziehen während live. Auf dem Hauptserver nur nach Tills OK.
- E2E 1600/1280/393/375: Studio als Admin und als Nutzer mit Recht. Ein Nutzer ohne Recht sieht keinen Reiter.

### Nicht in 3a
Mikrofon im Browser (3b), Jingles (3c), Wünsche (3d), Aufzeichnung der Sendung, mehrere Moderatoren gleichzeitig.

## Ausblick 3c / 3b / 3d (Bauplan-Nachtrag je Schritt)

- **3c Jingles:** Ordner aus der Bibliothek wählen oder Dateien hochladen (Moduldaten, MP3/FLAC/OGG, Größengrenze).
  Liquidsoap-Warteschlange „jingles“ über die Musik oder zwischen zwei Titel. Vorhören im Browser wie heute beim
  Bibliotheks-Vorhören.
- **3b Mikrofon im Browser:** Ton per WebSocket über HydraHive (Anmeldung + `radiostream.moderate`) an den
  Live-Eingang. **Vorab messen:** Opus/WebM im Browser → Liquidsoap, Verzögerung, Abbrüche, Handy. Erst danach Bauplan.
- **3d Wünsche:** Nutzer wünschen in der Bibliothek. Hörer-Wünsche über einen zweiten, engen Weg der Hörer-Seite
  (Suche + Wunsch, Bremse je Adresse, abschaltbar, **Standard aus**). Der Moderator nimmt an oder lehnt ab. Ohne
  Moderator plant der AutoDJ Wünsche selbst ein (Schalter). Sperren für Künstler und Titel gelten weiter.
