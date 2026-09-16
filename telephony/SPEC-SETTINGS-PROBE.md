# VoIP-Einstellungen: flüchtiger FRITZ!Box-Registrierungstest

## Was

Der vorhandene Reiter **VoIP → Einstellungen** erhält ein Formular für einen einmaligen
SIP-Registrierungstest gegen eine lokale FRITZ!Box. Der Benutzer gibt Registrar,
SIP-Port, Nebenstellen-Benutzername und Passwort ein und erhält ausschließlich einen
lokalisierten, stabilen Ergebnisstatus.

Der Test legt noch kein Telefonie-Projekt und keine dauerhafte Verbindung an. Benutzername
und Passwort werden weder im HydraHive-Credential-Store noch in Datenbank, Workspace,
Browser-Storage, Prozessargumenten, Environmentvariablen oder Logs gespeichert.

## Warum

Der Hardware-Spike muss aus der normalen HydraHive-Oberfläche bedienbar sein. Ein
Terminal-/Incus-Befehl ist kein akzeptabler Benutzerablauf. Gleichzeitig soll vor dem
ersten erfolgreichen FRITZ!Box-E2E-Test noch kein unvollständiger dauerhafter
Verbindungs-Lifecycle entstehen.

## Wie

### Frontend

- Der bestehende Platzhalter des Abschnitts `settings` wird durch eine eigene
  `RegistrationProbeSettings`-Komponente ersetzt.
- Registrar `192.168.3.1` und Port `5060` werden sichtbar, aber schreibgeschützt
  dargestellt; sie stammen aus der serverseitigen Spike-Allowlist.
- Benutzername und Passwort werden nie in `localStorage`, URL oder Query-Parametern
  abgelegt.
- Das Passwortfeld nutzt einen Passworttyp und wird nach jedem Versuch geleert.
- Während eines laufenden Tests sind Eingaben und Button gesperrt.
- Die Oberfläche erklärt ausdrücklich, dass dieser Spike nichts speichert.

### API

`POST /api/modules/telephony/spike/registration-test`

Request:

```json
{
  "registrar": "192.168.3.1",
  "port": 5060,
  "username": "********",
  "password": "********"
}
```

- aktueller HydraHive-Principal ist Pflicht;
- zusätzliche Felder werden abgewiesen;
- Registrar muss eine explizite RFC1918-IPv4-Adresse sein und exakt der serverseitigen
  Allowlist (`HH_TELEPHONY_SPIKE_REGISTRAR`, Default `192.168.3.1`) entsprechen;
- Port muss exakt dem allowlisteten Port (`HH_TELEPHONY_SPIKE_PORT`, Default `5060`)
  entsprechen; Benutzername und Passwort haben enge Grenzen und verhindern
  Config-Injection;
- Validierungsfehler werden sanitisiert und spiegeln niemals Request-Werte zurück;
- höchstens fünf Versuche pro Benutzer und Minute;
- nur ein Probe-Prozess läuft gleichzeitig.

Response:

```json
{"outcome": "registered"}
```

Zulässige Outcomes: `registered`, `auth_failed`, `registration_failed`, `timeout`,
`runtime_unavailable`, `busy`.

### Sidecar-Grenze

- HydraHive startet ausschließlich den fest konfigurierten Befehl
  `incus exec hh-telephony-spike -- .../stdin_probe.py` ohne Shell.
- Credentials werden als begrenztes JSON ausschließlich über `stdin` übertragen.
- Das Containerprogramm akzeptiert nur die vier erwarteten Felder, nutzt die bestehenden
  `ProbeTarget`-/`SipCredentials`-Validatoren und gibt nur einen stabilen Outcome aus.
- Rohe Baresip-Ausgaben bleiben im Containerprozess gekapselt.
- HydraHive erzwingt zusätzlich ein hartes Prozess-Timeout. Bleibt Baresip beim
  Deregistrieren hängen, wird ausschließlich der dedizierte Spike-Container kontrolliert
  gestoppt und neu gestartet; andere Container oder Hostprozesse bleiben unberührt.

## Akzeptanzkriterien

- [x] Der Reiter **Einstellungen** zeigt das Formular statt eines Platzhalters.
- [x] Nicht authentifizierte Requests erhalten HTTP 401.
- [x] Öffentliche oder nicht allowlistete private IPs, Hostnamen, abweichende Ports,
      CR/LF, Semikolon und zusätzliche JSON-Felder werden ohne Echo der Eingabe
      abgewiesen.
- [x] Credentialwerte erscheinen nicht in Repr, Response, Fehler, Args, Env oder Logs.
- [x] Passwort und Ergebnis werden nicht browserseitig persistiert.
- [x] Maximal fünf Versuche pro Benutzer und Minute sind möglich.
- [x] Parallelversuche liefern `busy`, statt einen zweiten Baresip-Prozess zu starten.
- [x] Fehlende Runtime liefert `runtime_unavailable` ohne interne Pfade oder stderr.
- [x] Der Sidecar-Prozess endet spätestens nach 30 Sekunden.
- [x] Tests, Ruff, TypeScript und Produktionsbuild sind grün.

## Nicht enthalten

- Speichern von SIP-Credentials
- Erzeugen eines Telefonie-Projekts oder Agenten
- dauerhafte SIP-Registrierung
- eingehende oder ausgehende Anrufe
- Audio-, RTP-, DTMF-, STT- oder TTS-Tests
- direkter Browserzugriff auf die FRITZ!Box
