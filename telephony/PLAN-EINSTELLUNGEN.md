# Plan: VoIP Etappe 1 – Einstellungen, Verbinden, Anleitung

Auftrag Till, 25.10.2026: Das Modul soll am Ende anrufen und Anrufe annehmen können, flexibel für
verschiedene Anlagen, zuerst für die FRITZ!Box. Heute: Unter „Einstellungen“ alle Zugangsdaten
eingeben, ein Knopf „Verbinden“ zum Einrichten, eine Anleitung auf der Einstellungsseite und ein
kurzer Hinweis, was bei einem Router zwischen FRITZ!Box und HydraHive zu beachten ist.

## Ziel dieser Etappe

Ein Kunde kann ohne Shell und ohne unseren Test-Container:

1. in der FRITZ!Box ein IP-Telefon anlegen (Anleitung auf der Seite),
2. in HydraHive alle Zugangsdaten eintragen und speichern (Passwort verschlüsselt, nie zurück),
3. auf **Verbinden** klicken. HydraHive meldet sich als IP-Telefon an der FRITZ!Box an und bleibt
   angemeldet, auch nach einem Neustart.
4. Er sieht klar den Stand: verbunden / Benutzername oder Kennwort falsch / FRITZ!Box nicht
   erreichbar / abgelehnt, mit einem Satz, was zu tun ist.
5. Er kann trennen und die Zugangsdaten löschen.

Anrufe annehmen und anrufen kommen in den nächsten Etappen (siehe unten). Ruft in dieser Etappe
jemand die Nummer an, lehnt HydraHive höflich mit „nicht verfügbar“ (480) ab. Andere Telefone
klingeln normal weiter.

## Entscheidungen

- **SIP-Anmeldung in Python, im Modul selbst.** Ohne Container, ohne Baresip-Build. Sie läuft gleich auf
  Linux und Mac. Ein eigener Thread pro Verbindung hält einen festen UDP-Port offen, meldet sich an
  (REGISTER mit Digest/MD5), erneuert die Anmeldung vor Ablauf und meldet beim Trennen ab
  (Expires 0). Der Code ist klein und ohne fremde Abhängigkeiten. Auf demselben Port nehmen wir
  in Etappe 2 die Anrufe an. Der Baresip-Spike bleibt als Entwicklerwerkzeug.
- **Flexibel:** Feld „Anlage“ mit „FRITZ!Box“ (jetzt) und „Andere SIP-Anlage“, technisch gleich. Die
  Anleitung zeigt nur FRITZ!Box. Wird ein Feld nur für die FRITZ!Box gebraucht, ist es so gekennzeichnet.
- **Wer darf einrichten:** Modul-Freigabe `module.telephony`, Standard **nur Admins**. Grund: Anrufe
  kosten Geld. Jeder Nutzer hat höchstens **eine** Verbindung (Inhaber `user:<name>`). Die
  Anbindung an Telefonie-Projekte und Mitglieder (SPEC-V1 §6) folgt in einer späteren Etappe.
- **Nur Heimnetz:** Anlagenadresse muss `fritz.box` oder eine private Adresse sein (RFC 1918,
  aufgelöst und geprüft, verbunden wird mit der geprüften IP). Keine Verbindung ins Internet
  (SPEC-V1 §2.14, §16.4).
- **Bisheriger Test-Reiter** (Spike-Container) verschwindet aus der Oberfläche, er läuft beim Kunden
  nicht. Die Spike-Routen bleiben für uns.

## Felder

| Feld | Pflicht | Standard | Hinweis |
|---|---|---|---|
| Anlage | ja | FRITZ!Box | FRITZ!Box / Andere SIP-Anlage |
| Anzeigename | nein | „HydraHive“ | nur zur Anzeige |
| Adresse der Anlage | ja | `fritz.box` | oder IP, z. B. 192.168.178.1 |
| SIP-Port der Anlage | ja | 5060 | |
| Benutzername | ja | – | FRITZ!Box: mind. 8 Zeichen |
| Kennwort | ja (beim Anlegen) | – | verschlüsselt, nie zurückgegeben |
| Eigene Rufnummer | nein | – | zur Anzeige und später für ausgehende Anrufe |
| Lokaler SIP-Port (HydraHive) | ja | 5070 | für Weiterleitungen am Router |
| Sprach-Ports (RTP) von–bis | ja | 7078–7109 | für Weiterleitungen am Router, wird in Etappe 2 genutzt |
| Anmeldung erneuern alle | ja | 300 s | 60–3600 |

## Dateien

- `migrations/001_telephony.sql` – Tabelle `module_telephony_connections`
- `backend/secrets.py` – AES-GCM, eigener HKDF-Schlüssel, Verbindungs-ID als AAD (wie Mailbox)
- `backend/conn_models.py` – Eingabe-/Ausgabemodelle, Feldprüfung
- `backend/netguard.py` – Adresse nur Heimnetz, Ports
- `backend/sip/message.py` – SIP-Nachrichten bauen/lesen (nur was REGISTER/Antworten braucht)
- `backend/sip/digest.py` – Digest-Auth (MD5, qop=auth)
- `backend/sip/register.py` – ein Anmeldevorgang über einen Socket → Ergebnis-Code
- `backend/sip/agent.py` – Thread pro Verbindung: anmelden, erneuern, abmelden, 480 auf INVITE, 200 auf OPTIONS
- `backend/connections.py` – speichern, ändern, löschen, Status
- `backend/conn_manager.py` – Threads zu gespeicherten Verbindungen passend halten (Modul-Job)
- `backend/conn_routes.py` – API
- `frontend/ConnectionSettings.tsx`, `frontend/_ConnectionForm.tsx`, `frontend/_ConnectionStatus.tsx`,
  `frontend/SetupGuide.tsx`, `frontend/RouterHint.tsx`, `frontend/i18n.ts` (DE/EN)
- Tests je Datei, inkl. echtem UDP-Registrar im Test (Digest-Challenge, 200/403/Timeout)

## API (`/api/modules/telephony`)

- `GET /connection` – eigene Verbindung (ohne Kennwort, `has_password: true`) + Status
- `PUT /connection` – anlegen/ändern; Kennwort leer = unverändert
- `POST /connection/connect` – anmelden (wartet höchstens 10 s auf das Ergebnis), danach dauerhaft angemeldet
- `POST /connection/disconnect` – abmelden, bleibt gespeichert
- `DELETE /connection` – abmelden + löschen
- Fehlertexte nie mit Kennwort, SIP-Challenge oder Rohantwort. Ratenbegrenzung auf connect.

## Status-Codes

`not_configured`, `disconnected`, `connecting`, `registered`, `auth_failed` (401/403 nach
Anmeldedaten), `not_found` (404, Benutzer unbekannt), `unreachable` (keine Antwort), `rejected`
(andere 4xx/5xx), `blocked` (Adresse nicht im Heimnetz), `port_in_use`.

## Anleitung auf der Einstellungsseite (FRITZ!Box, nach AVM-Wissensdatenbank #42)

1. FRITZ!Box-Oberfläche → Telefonie → Telefoniegeräte → „Neues Gerät einrichten“
2. „Telefon (mit und ohne Anrufbeantworter)“ → „LAN/WLAN (IP-Telefon)“
3. Benutzername (mind. 8 Zeichen) und Kennwort (mind. 8 Zeichen, anders als Benutzername) vergeben
4. Rufnummer für ausgehende Gespräche und Rufnummern, auf die HydraHive reagieren soll, wählen →
   „Übernehmen“, ggf. an der FRITZ!Box bestätigen
5. Hier Adresse (`fritz.box` oder IP), Benutzername und Kennwort eintragen → Speichern → Verbinden
6. Hinweis: Auslands- und Sonderrufnummern sind für IP-Telefone standardmäßig gesperrt (so lassen).

## Hinweis „Router dazwischen“ (kurz, einklappbar)

- Am einfachsten: HydraHive im selben Netz wie die FRITZ!Box.
- Sonst muss der Router zwischen beiden Netzen durchlassen: SIP (UDP, Port der FRITZ!Box 5060 ↔
  lokaler SIP-Port von HydraHive) und Sprache (UDP, Sprach-Ports von HydraHive ↔ FRITZ!Box).
  Mit NAT am Router: diese Ports an den HydraHive-Server weiterleiten.
- SIP-ALG / „SIP-Helfer“ am Router ausschalten.
- Lehnt die FRITZ!Box die Anmeldung aus einem anderen Netz ab: beim IP-Telefon unter
  „Anmeldedaten“ prüfen. Nie SIP-Ports der FRITZ!Box ins Internet freigeben.
- Typisches Zeichen für ein Router-Problem: verbunden, Anruf kommt an, aber kein Ton.

## Implementierungsreihenfolge (TDD: rot → grün → Mutantenprobe)

1. Migration + `secrets.py` (Tests: Verschlüsselung, falsche ID, kein Klartext)
2. `conn_models.py` + `netguard.py` (Tests: Pflichtfelder, Ports, Bereich, öffentliche Adresse/Hostname blockiert)
3. `sip/message.py` + `sip/digest.py` (Tests gegen RFC-2617-Beispiel und eigene Vektoren)
4. `sip/register.py` (Tests gegen echten UDP-Fake-Registrar: 200, 401→200, 401→403, 404, Timeout, rport)
5. `sip/agent.py` + `conn_manager.py` (Tests: erneuert vor Ablauf, Trennen sendet Expires 0, INVITE → 480, Neustart verbindet wieder)
6. `connections.py` + `conn_routes.py` (Tests: nur eigene, Kennwort nie in Antwort/Log, Ratenbegrenzung, Löschen)
7. Frontend (vitest: Formular, Kennwortfeld leer bei vorhandenem Kennwort, Status-Texte, Anleitung, Router-Hinweis)
8. Status/Übersicht ehrlich anpassen, Version 0.6.0, Katalogtext „in Entwicklung: Anrufe folgen“
9. Live: echte FRITZ!Box (Till trägt die Zugangsdaten selbst in der Oberfläche ein), Linux + Mac

## Akzeptanzkriterien

- Alle Felder speicherbar; Kennwort nie in API-Antwort, Log oder Fehlermeldung
- „Verbinden“ an echter FRITZ!Box → „Verbunden“; falsches Kennwort → „Benutzername oder Kennwort falsch“
- Verbindung bleibt über Stunden und über einen Neustart bestehen
- Trennen meldet ab (in der FRITZ!Box wird das IP-Telefon nicht mehr als angemeldet angezeigt)
- Öffentliche Adressen werden abgelehnt
- Tests, ruff, tsc/eslint/vitest grün; Mutantenprobe

## Nächste Etappen (nicht in diesem Plan)

- **Etappe 2 – Anrufe annehmen:** INVITE annehmen, Ton (RTP, G.711), Ansage, Testanruf-Knopf mit
  „Ton gehört?“, danach Telefon-Agent (Sprache → Text → Agent → Sprache).
- **Etappe 3 – Anrufen:** ausgehender Anruf mit Freigabe, Grenzen und Sperren aus SPEC-V1 §16.2.
- **Etappe 4:** Telefonaufträge, Gesprächsliste, Archiv, Projekte und Mitglieder (SPEC-V1).
