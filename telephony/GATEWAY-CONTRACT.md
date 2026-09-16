# HydraHive-Telefonie-Gatewayvertrag

**Stand:** Vertrag 1 · **Modul:** `telephony` 0.4.2

## Zweck und Grenze

Der Gatewayvertrag trennt HydraHive-Fachdaten von SIP, RTP, Codecs, STT und TTS.
HydraHive entscheidet über Benutzer, Projekte, Freigaben, Aufträge und Aufbewahrung. Ein
Gateway führt nur ausdrücklich adressierte Telefonieoperationen aus und liefert
beobachtete Ereignisse zurück.

Version 0.2.0 führte den Python-Port, strikte Modelle und einen In-Process-Fake ein.
Version 0.3.0 ergänzte einen authentifizierten, flüchtigen Registrierungs-Spike.
Version 0.4.0 ergänzt Gate 2: ein explizites Testfenster nimmt genau einen eingehenden
Anruf mit sendonly-Testton an und beendet ihn automatisch. Version 0.4.1 nutzt für Gate 2
SIP über TCP. Version 0.4.2 aktiviert zusätzlich SIP Outbound nach RFC 5626 inklusive
stabiler UUID, damit die FRITZ!Box den INVITE über den registrierten TCP-Flow und nicht
an die private Contact-Adresse zurücksendet. Gate 1 bleibt UDP. Beide Tests laufen über
die isolierte Developer-Runtime, speichern keine Credentials und öffnen keinen
dauerhaften Dienst. Produktive Anruffunktionen bleiben deaktiviert.

## Identitäten

Jede Verbindung wird durch das unveränderliche Paar `(project_id, connection_id)`
adressiert. Jeder Call trägt zusätzlich `call_id`, `attempt_id` und `direction`.
Implementierungen müssen die vollständige Referenz vergleichen; ein passender `call_id`
allein berechtigt niemals zum Zugriff auf einen Call eines anderen Projekts.

Alle IDs sind UUIDs. Sie werden von HydraHive erzeugt, nicht vom LLM und nicht aus einer
Rufnummer abgeleitet.

## Operationen

Der asynchrone Port `TelephonyGateway` umfasst:

- `health()` — technische Bereitschaft und ehrlicher Realtest-Status
- `probe(connection)` — flüchtiger Verbindungstest ohne Registrierung oder Persistenz
- `register(connection)` — SIP/PBX-Verbindung aktivieren
- `pause(connection)` — Registrierung pausieren
- `dial(request)` — genau einen ausgehenden Versuch starten
- `answer(call)` / `reject(call)` — eingehenden Call behandeln
- `hangup(call)` — einen Call idempotent beenden
- `speak(request)` / `stop_speaking(call)` — TTS-Ausgabe starten beziehungsweise für
  Barge-in stoppen
- `events()` — geordneter Strom beobachteter Gatewayereignisse

## Idempotenz

`attempt_id` ist der Idempotency-Key für einen Rufversuch:

- dieselbe `attempt_id` mit demselben vollständigen `DialRequest` liefert denselben Call
  zurück und startet keinen zweiten Anruf;
- dieselbe `attempt_id` mit anderer Call-ID, Verbindung, Projekt-ID oder Zielnummer wird
  als `attempt_conflict` abgewiesen;
- `hangup` und das Stoppen bereits gestoppter Wiedergabe sind idempotent.

Ein späterer Netzwerkadapter muss diesen Vertrag über Prozessneustarts hinweg erhalten.
Der In-Process-Fake beweist nur die Semantik innerhalb seiner Lebensdauer.

## Ereignisse und Reihenfolge

Unterstützte Ereignisse:

- Aufbau: `incoming`, `dialing`, `ringing`, `connected`
- Sprache: `speech.partial`, `speech.final`
- Wiedergabe: `playback.started`, `playback.stopped`
- Leitung: `dtmf`, `voicemail.detected`, `busy`, `no_answer`, `rejected`, `failed`,
  `disconnected`

Jedes Ereignis trägt die vollständige Call-Referenz, eine bei 1 beginnende und pro Call
streng steigende Sequenznummer sowie einen zeitzonenbewussten UTC-Zeitstempel.
Netzwerktransporte dürfen mindestens-einmal zustellen; HydraHive dedupliziert später über
`(call_id, sequence)`. Eine Sequenzlücke darf nicht still übersprungen werden, sondern
muss einen Resync oder einen sichtbar fehlgeschlagenen Call auslösen.

Freie, unbegrenzte Payload-Dictionaries sind bewusst nicht Teil des Vertrags. Sprache,
DTMF, Rufnummer und Fehlergrund besitzen begrenzte, typisierte Felder. `speech.*` verlangt
ein Transkript, `incoming` eine E.164-Gegenstelle und `failed` einen stabilen Fehlercode.

## Credential- und Netzwerkgrenze

`ConnectionSpec` hält SIP-Benutzername und Passwort als `SecretStr`; Darstellung und
JSON-Ausgabe sind maskiert. Fake, Probe und registrierte Referenzen bewahren keine
Credentials auf. Produktionsadapter dürfen Zugangsdaten ausschließlich für den konkreten
Verbindungsaufbau verwenden und nie in Events, Logs oder Fehlermeldungen aufnehmen.

Für den späteren Prozessadapter gelten zusätzlich:

1. standardmäßig Unix-Socket oder Loopback;
2. auf einem separaten LAN-Host mTLS oder rotierbare Maschinenidentität;
3. feste Ziel-Allowlist, kein benutzerkontrolliertes allgemeines Proxying;
4. keine FRITZ!Box-/PBX-Freigabe ins Internet;
5. strukturierte Fehlercodes statt Providerantworten mit möglicherweise sensiblen Daten.

Host-/Netzwerk-Allowlisting und Secret-Entschlüsselung gehören in den noch ausstehenden
Setup-/Secret-Store-Service, nicht in den reinen Vertrag.

## Fake-Semantik

`FakeTelephonyGateway` führt keinerlei Netzwerk- oder Audiooperation aus. Er:

- speichert nur Connection-Referenzen, niemals Zugangsdaten;
- erzwingt Registrierung vor Calls;
- simuliert eingehende Calls explizit über `inject_incoming`;
- prüft Zustandsübergänge und vollständige Projektbindung;
- erzeugt deterministische, monotone Ereignisse;
- kennzeichnet `live_telephony_verified` immer als `false`.

Der Fake ist die Referenz für Contract-Tests. Ein späterer Sidecar-Adapter muss dieselben
Tests gegen seine Testinstanz bestehen, bevor er in den Setupflow aufgenommen wird.
