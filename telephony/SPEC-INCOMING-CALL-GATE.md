# Spezifikation: Gate 2 – kontrollierter eingehender Testanruf

**Status:** freigegeben · **Entscheidung:** Option B (Annehmen + kurzer Testton)

## 1. Problem

Gate 1 beweist nur, dass sich die dedizierte SIP-Nebenstelle an der FRITZ!Box
registrieren kann. Noch unbewiesen ist, ob die FRITZ!Box einen eingehenden Anruf an den
isolierten Baresip-Sidecar zustellt und ob dieser ihn kontrolliert annehmen und beenden
kann.

Gate 2 muss diesen Pfad nachweisen, ohne daraus bereits einen dauerhaften
Telefoniedienst zu machen und ohne Anruferaudio, Rufnummern oder Zugangsdaten zu
persistieren.

## 2. Geprüfte Optionen

### A. Anruf nur erkennen

- kleinste Netzwerkfläche
- beweist ausschließlich INVITE-Zustellung
- beweist weder Annahme noch den vom Anrufer wahrnehmbaren Pfad

### B. Kontrolliert annehmen und Testton senden – gewählt

- temporäres Testfenster
- maschinenlesbare Baresip-Ereignisse
- Annahme mit ausschließlich ausgehendem Audio
- kurzer Sinuston bestätigt dem Anrufer die erfolgreiche Annahme
- danach automatisches Auflegen und Runtime-Neustart

### C. Dauerhafter Gateway-Daemon

- wäre näher an der späteren Produktarchitektur
- benötigt bereits persistente Verbindung, Secret Store, Lifecycle und Eventtransport
- für Gate 2 zu großer und sicherheitskritischer Scope

## 3. Operatorablauf

1. Benutzer öffnet **VoIP → Einstellungen**.
2. Benutzer gibt die dedizierten Nebenstellen-Credentials erneut ein.
3. Benutzer startet **Eingehenden Anruf testen**.
4. Die UI fordert dazu auf, innerhalb des begrenzten Testfensters die der Nebenstelle
   zugewiesene Rufnummer anzurufen.
5. Der Sidecar registriert sich flüchtig und wartet auf genau einen eingehenden Anruf.
6. Der Anruf wird mit `audio=sendonly` und deaktiviertem Video angenommen.
7. Baresip sendet etwa drei Sekunden lang einen neutralen Sinuston.
8. Der Sidecar legt auf und liefert ausschließlich einen stabilen Ergebniscode.
9. HydraHive stoppt und startet den dedizierten Spike-Container, damit kein Baresip-
   Prozess und kein Secret im Prozessspeicher verbleibt.

## 4. Architektur

```text
Browser (Credentials nur React-State)
  │ POST /api/modules/telephony/spike/incoming-test
  ▼
HydraHive Telephony Backend
  ├── Auth + Requestlimit + Ziel-Allowlist
  ├── gemeinsamer Single-Probe-Lock
  └── feste incus-exec-Argumentliste, stdin JSON
       ▼
hh-telephony-spike
  ├── stdin-Adapter mit Größen-/Schema-Limit
  ├── temporäre 0600-Konfiguration in /dev/shm
  ├── Baresip + ctrl_tcp nur auf 127.0.0.1
  ├── strukturierte Netstring-/JSON-Ereignisse
  └── ausine-Testton, keine Audioaufnahme
```

Der Baresip-stdout/stderr wird für diesen Test verworfen. Der Wrapper wertet nur
strukturierte `ctrl_tcp`-Nachrichten aus und gibt niemals deren Rohinhalt nach außen.

## 5. State Machine

```text
starting
  -> registration_failed | auth_failed | waiting
waiting
  -> no_incoming_call | answering | caller_cancelled
answering
  -> incoming_answered | answer_failed | caller_cancelled
alle Endzustände
  -> Sidecar-Restart durch Backend
```

Relevante Baresip-Ereignisse:

- `REGISTER_OK`
- `REGISTER_FAIL`
- `CALL_INCOMING`
- `CALL_ESTABLISHED`
- `CALL_CLOSED`

Der aus einem Event übernommene Baresip-Call-Identifier wird vor Verwendung in einem
Steuerbefehl auf eine enge Zeichen-Allowlist und Maximallänge geprüft. Caller-ID,
Displayname, Peer-URI und Providertexte werden nicht zurückgegeben oder gespeichert.

## 6. Stabile Ergebnisse

- `incoming_answered` – angenommen, Testtonphase erreicht, anschließend beendet
- `no_incoming_call` – innerhalb des Fensters kein Anruf
- `caller_cancelled` – Anrufer hat vor erfolgreicher Annahme aufgelegt
- `answer_failed` – kontrollierte Annahme oder Zustandsübergang fehlgeschlagen
- bestehend: `auth_failed`, `registration_failed`, `timeout`, `runtime_unavailable`,
  `busy`

Die HTTP-Antwort enthält ausschließlich `{"outcome":"<code>"}`.

## 7. Sicherheitsgrenzen

- Endpoint erfordert einen authentifizierten HydraHive-Principal.
- Registrar/Port müssen exakt der Startup-Allowlist entsprechen.
- Höchstens fünf Versuche pro Benutzer und Minute.
- Registrierungs- und Eingangstests teilen denselben Prozesslock.
- Credentials laufen nur über Requestbody → stdin → 0600-Datei in `/dev/shm`.
- Keine Credentials in argv, Environment, URL, Response oder Logs.
- `ctrl_tcp` bindet ausschließlich an `127.0.0.1` im dedizierten Container.
- Genau eine lokale Control-Verbindung und ein eingehender Call werden verarbeitet.
- Audio ist `sendonly`: kein Anruferaudio wird abgespielt, aufgezeichnet oder gespeichert.
- Video ist deaktiviert.
- Kein automatisches Antworten außerhalb des expliziten Testfensters.
- Harte Zeitgrenzen auf Wrapper-, Backend- und Container-Cleanup-Ebene.
- Nach jedem Gate-2-Versuch wird ausschließlich `hh-telephony-spike` neu gestartet.

## 8. Akzeptanzkriterien

- [ ] UI zeigt einen separaten Eingangstest und eine klare Jetzt-anrufen-Anweisung.
- [ ] Ohne Authentifizierung liefert der Endpoint HTTP 401.
- [ ] Ziel-Allowlist, Requestlimit und Secret-Redaction aus Gate 1 bleiben wirksam.
- [ ] `ctrl_tcp` ist nur auf Container-Loopback erreichbar.
- [ ] Ein eingehender Testanruf wird kontrolliert mit sendonly-Testton angenommen.
- [ ] Der Call wird nach ungefähr drei Sekunden automatisch beendet.
- [ ] Caller-ID und Providerrohdaten erscheinen nicht in API-Antworten oder Logs.
- [ ] Kein Anruferaudio wird gespeichert.
- [ ] Kein Baresip-Prozess und kein temporäres Config-Verzeichnis bleibt zurück.
- [ ] Unit-, API-, Sidecar-, Frontend- und lokaler Fake-SIP-E2E-Test sind grün.

## 9. Nicht enthalten

- dauerhafte SIP-Registrierung oder Autostart
- Speicherung der Nebenstellen-Credentials
- eingehendes Audio, Aufnahme oder Transkription
- Spracheingabe, STT, TTS oder Agentenantworten
- beliebige Anrufweiterleitung
- ausgehende Anrufe
- produktiver Gateway-Netzwerkdienst
