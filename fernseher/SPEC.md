# Fernseher – Sony BRAVIA im Heimnetz steuern

> Neues Modul `fernseher`. Idee von Till (29.10.2026): Den Android-Fernseher im Wohnzimmer aus HydraHive heraus
> steuern, über Agenten und später über die Voice-Boxen. Task 8af6dda1.
> **Status: Plan. Gebaut wird erst nach Tills Freigabe, Etappe für Etappe.**

## Problem

Im Heimnetz hängt ein Sony BRAVIA (KD-60XF8305, Android TV, 2018). HydraHive kann ihn heute nicht ansprechen:
- Ein Agent kann nicht sagen, was gerade läuft.
- Er kann nicht umschalten, leiser machen oder den Fernseher ausschalten.

Home Assistant könnte das zwar, aber nur über allgemeine Befehle mit Sony-Kürzeln, die ein Agent schlecht trifft.

## Ziel

- **Agenten** steuern den Fernseher mit klaren Werkzeugen: „schalte auf ZDF“, „mach leiser“, „Fernseher aus“,
  „starte Plex“, „was läuft gerade?“.
- **Eine eigene Seite** zeigt, was gerade läuft, und dient als Fernbedienung: Sender, Lautstärke, Ein/Aus, Apps.
- **Einrichtung nur über die Oberfläche:** Adresse und Schlüssel des Fernsehers eintragen, „Verbindung testen“.
  Kein Terminal, keine Datei.
- **Später:** Voice-Boxen („Fernseher leiser“) und Ansagen per Cast. Diese Etappen kommen erst nach Etappe 1.

## Befund (29.10.2026, am echten Gerät gemessen)

- Adresse 192.168.178.186. Sony-Schnittstelle `http://<ip>/sony/<dienst>`, JSON-RPC, `interfaceVersion` 5.4.0.
- Anmeldung über die Kopfzeile `X-Auth-PSK: <Schlüssel>`. Den Schlüssel stellt man am Fernseher ein:
  Einstellungen → Netzwerk → Heimnetzwerk → IP-Steuerung → „Normal und Pre-Shared Key“.
- **Wichtig:** Nach dem Einschalten der IP-Steuerung meldete der Fernseher für alle Dienste 404, bis er ganz neu
  gestartet wurde (Netzstecker). Das muss die Oberfläche als Hinweis zeigen, wenn genau dieser Fehler kommt.
- Gemessen und funktioniert:

| Zweck | Dienst · Methode · Version | Ergebnis |
|---|---|---|
| Modell | `system` · `getInterfaceInformation` · 1.0 | ohne Schlüssel: Modell KD-60XF8305 |
| An/aus? | `system` · `getPowerStatus` · 1.0 | `active` bzw. `standby` |
| Systemdaten | `system` · `getSystemInformation` · 1.0 | nur mit Schlüssel (sonst 403) |
| Was läuft | `avContent` · `getPlayingContentInfo` · 1.0 | Platz, Sender, Sendung, `uri` |
| Senderliste | `avContent` · `getContentList` · **1.0/1.2** | `{"source":"tv:dvbt","stIdx":0,"cnt":N}`; 1.5 → „Illegal Argument“ |
| Umschalten | `avContent` · `setPlayContent` · 1.0 | `{"uri": "tv:dvbt?trip=…&srvName=…"}` – bestätigt (SAT.1 → kabel eins → SAT.1) |
| Lautstärke | `audio` · `getVolumeInformation` · 1.0 | `speaker` 14 |
| Apps | `appControl` · `getApplicationList` · 1.0 | 22 Apps (Plex, Emby, Netflix, YouTube …) |

- **Nicht** gewirkt: die nachgebaute Fernbedienungstaste (IRCC „ChannelUp“). HTTP 200, aber kein Wechsel. Etappe 1
  verwendet deshalb nur die JSON-Methoden. Lautstärke-Setzen, Ein/Aus und App-Start sind noch nicht am Gerät
  erprobt, das passiert in der Probe von Etappe 1.

## Etappe 1 (dieser Plan): Steuern über Werkzeuge und eine Seite

### Einstellungen

- Ein Fernseher je Installation, in Etappe 1 kein Mehrgeräte-Betrieb: Name, Adresse (IP oder Hostname im Heimnetz)
  und Schlüssel.
- Der Schlüssel wird mit dem Master-Schlüssel des Kerns **verschlüsselt** gespeichert (AES-GCM, eigener abgeleiteter
  Schlüssel wie bei `telephony/backend/secrets.py`).
- Der Schlüssel verlässt den Server nie: Die Oberfläche sieht nur „gesetzt / nicht gesetzt“. Er erscheint nicht in
  Logs, Fehlermeldungen oder Werkzeug-Ergebnissen.
- Die Adresse muss im Heimnetz liegen (private IPv4, `.local`/Hostname). Öffentliche Adressen werden abgelehnt,
  damit das Modul nicht als Tür nach außen dient.
- „Verbindung testen“ liefert Modell, An/aus und eine klare Meldung bei falschem Schlüssel (403), nicht erreichbar
  (Zeitüberschreitung) oder bei „IP-Steuerung erst nach Neustart aktiv“ (404 auf allen Diensten).

### Werkzeuge für Agenten

| Werkzeug | Macht | Recht |
|---|---|---|
| `tv_status` | An/aus, was läuft (Platz, Sender, Sendung), Lautstärke, stumm | lesen |
| `tv_sender_liste` | Senderliste (Platz + Name) | lesen |
| `tv_sender` | Umschalten per Name („ZDF“, „zdf hd“) oder Platz (2). Unscharfer Abgleich; bei mehreren Treffern nachfragen statt raten | schalten |
| `tv_lautstaerke` | Wert 0–100 oder `+n`/`-n`, stumm an/aus | schalten |
| `tv_power` | an / aus (Standby) | schalten |
| `tv_app` | App starten per Name aus der App-Liste; ohne Name → Liste | schalten |

- Jedes schaltende Werkzeug **liest danach nach** und meldet den echten neuen Zustand, nicht nur „gesendet“.
- Schutz gegen Fehlbedienung: Lautstärke höchstens 60 je Befehl (Hörschutz, Nachbarn) und höchstens ±20 auf einmal.
  Die Grenze steht in den Einstellungen und ist veränderbar.

### Freigaben (wie beim Home-Assistant-Modul)

- `module.fernseher` (Seite und lesende Werkzeuge): alle angemeldeten Nutzer.
- `fernseher.control` (schalten): **nur Admin** voreingestellt, in der Admin-Konsole an andere freigebbar.
- Einstellungen ändern: nur Admin.

### Seite „Fernseher“ (Bereich `zuhause`)

- Karte „Läuft gerade“: Sender, Sendung, Lautstärke, An/aus.
- Fernbedienung: Ein/Aus, Lauter/Leiser/Stumm, Senderliste zum Antippen, App-Liste.
- Einrichten: Name, Adresse, Schlüssel (Feld leert sich nach dem Speichern), „Verbindung testen“.
- Einfache Sprache, Deutsch und Englisch, ohne Fachwörter. Kein Hinweis auf Terminal oder Dateien.
- Handy-tauglich (393 und 375 px), weil man so eine Fernbedienung am Handy benutzt.

### Fehlercodes (Deutsch und Englisch)

- `tv_not_configured` (noch nicht eingerichtet)
- `tv_unreachable` (Fernseher aus oder nicht im Netz)
- `tv_auth_failed` (Schlüssel falsch)
- `tv_needs_restart` (IP-Steuerung erst nach Neustart des Fernsehers aktiv)
- `tv_address_not_local` (Adresse nicht im Heimnetz)
- `tv_channel_unknown` (Sender nicht gefunden)
- `tv_channel_ambiguous` (mehrere passende Sender)
- `tv_app_unknown` (App nicht gefunden)
- `tv_volume_limit` (über der Lautstärke-Grenze)
- `tv_upstream_error` (sonstige Antwort des Fernsehers)

### Daten

- Tabelle `module_fernseher_settings` (eine Zeile): Name, Adresse, verschlüsselter Schlüssel, Lautstärke-Grenze,
  geändert am/von.
- Senderliste und App-Liste werden nicht gespeichert, sondern jedes Mal frisch vom Fernseher geholt. Höchstens 60 s
  im Speicher, damit der Agent nicht bei jedem Schritt neu fragt.

## Später (eigene Etappen, nicht Teil dieses Plans)

- **Etappe 2 – Voice:** Sprachbefehle der Voice-Boxen („Fernseher leiser“) über die Werkzeuge aus Etappe 1.
- **Etappe 3 – Cast:** Ansagen der Sprachausgabe und Musik über Google Cast auf dem Fernseher.
- **Etappe 4 – mehrere Fernseher** und weitere Marken (Android-TV-Fernbedienung, Kopplung per Code).

## Nicht Ziel

- Das Betriebssystem des Fernsehers verändern, Apps per Sideload installieren oder ADB nutzen.
- Fernsehen aufnehmen oder Bilder vom Fernseher abgreifen.

## Prüfung (Etappe 1)

- Rote Tests zuerst. Der Fernseher wird in den Tests nachgebaut, kein echter Netzverkehr. Mutanten.
- Schlüssel-Schutz:
  - Er steht nach dem Speichern nicht im Klartext in der Datenbank.
  - Keine Route und kein Werkzeug gibt ihn zurück.
  - Er fehlt in Fehlermeldungen.
- Freigaben: Ein Nicht-Admin bekommt beim Schalten 403, Lesen geht.
- Adressprüfung: Öffentliche IPs und Namen, die nach außen zeigen, werden abgelehnt.
- `scripts/check_test_safety.py`, `scripts/check_version_bump.py`, `scripts/tests` grün. Eintrag in `hub.json`,
  `NAV_AREA.de.md`, `test_nav_area.py`.
- **Probe am echten Fernseher** (Till sitzt davor): Status, Senderwechsel hin und zurück, Lautstärke ±1 und zurück,
  stumm an/aus, App-Liste. Ein/Aus und App-Start nur mit Tills OK im Moment des Tests.
- E2E der Seite bei 1600, 1280, 393 und 375 px nur über sichtbare Texte.
