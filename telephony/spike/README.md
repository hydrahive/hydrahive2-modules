# FRITZ!Box SIP Spike Harness

Dieser Ordner ist ein isoliertes Developer-Werkzeug für Gates 1 und 2 des
Telefonie-Spikes. Er ist **kein** Teil der installierten Produktions-Runtime. Der Harness
baut Baresip 4.11.0 und libre 4.11.0 in einem separaten, unprivilegierten
Incus-Container. Er prüft eine SIP-Registrierung sowie genau einen kontrollierten
eingehenden Testanruf per UDP/G.711.

## Sicherheitsregeln

- Nebenstellen-Benutzername und -Passwort niemals in Chat, Issue, Shellargument,
  Environmentvariable oder Datei im Workspace eintragen.
- Das CLI akzeptiert Credentials ausschließlich verdeckt über ein interaktives TTY.
- Temporäre Baresip-Dateien liegen in `/dev/shm`, haben Modus `0600` und werden nach dem
  Lauf gelöscht.
- Rohe Baresip-/SIP-Logs werden nicht ausgegeben oder persistiert; SIP-Trace ist aus.
- Der Registrar muss eine explizite RFC1918-IPv4-Adresse sein. Öffentliche Ziele und
  Hostnamen werden abgewiesen.
- Der Build überschreibt niemals einen Container namens `hh-telephony-spike`.
- Die Baresip-Steuerung bindet nur auf `127.0.0.1` im Container.
- Gate 2 verwendet ausschließlich sendonly-Testaudio. Anruferaudio wird weder
  abgespielt noch aufgezeichnet oder gespeichert.

## 1. Runtime einmalig vorbereiten

Im Repository `hydrahive2-modules`:

```bash
chmod +x telephony/spike/prepare-runtime.sh telephony/spike/run-probe.sh
./telephony/spike/prepare-runtime.sh
```

Nach einem Modulupdate wird eine bestehende dedizierte Runtime ohne Neubuild mit den
aktuellen, credentialfreien Harness-Dateien synchronisiert:

```bash
./telephony/spike/sync-runtime.sh
```

Das Script prüft Containername und Baresip-Version, bevor es ausschließlich die
Spike-Dateien ersetzt.

Der Build ist auf diese Releases und Commits gepinnt:

- Baresip 4.11.0: `3d30821f099925d24167f8a99e93ba4d1be98599`
- libre 4.11.0: `ceefe9ff499aa1bcfb6255aff1737434dd385322`

Das veraltete Ubuntu-Baresip-Paket wird nicht installiert.

## 2. Registrierung über HydraHive prüfen

Der normale Benutzerablauf liegt unter **VoIP → Einstellungen → FRITZ!Box-Verbindung
testen**. Das authentifizierte Backend überträgt die vier begrenzten Eingabefelder nur
über `stdin` in diesen Container und gibt ausschließlich einen stabilen Ergebniscode an
die Oberfläche zurück. Die Zugangsdaten werden nicht gespeichert.

Der folgende Terminalbefehl bleibt ausschließlich als Developer-Fallback bestehen:

```bash
incus exec hh-telephony-spike -- \
  /opt/hh-telephony-spike/spike/run-probe.sh \
  --registrar 192.168.3.1
```

Beide CLI-Eingaben bleiben unsichtbar. Erlaubt sind beim Benutzernamen 8–64 Zeichen
(`A-Z`, `a-z`, `0-9`, Punkt, Unterstrich, Bindestrich). Das Passwort muss 12–128 Zeichen
lang sein und darf keine Leerzeichen, Semikolons, Anführungszeichen oder Backslashes
enthalten. Ein zufälliges alphanumerisches Passwort mit mindestens 20 Zeichen ist die
einfachste sichere Wahl.

Das CLI gibt ausschließlich einen stabilen Code aus:

| Code | Bedeutung | Exit-Code |
|---|---|---:|
| `registered` | Gate 1 bestanden | 0 |
| `auth_failed` | Zugangsdaten oder FRITZ!Box-Berechtigung prüfen | 2 |
| `registration_failed` | Registrar/Netz/SIP fehlgeschlagen | 3 |
| `no_result` | kein eindeutiges Ergebnis | 3 |
| `timeout` | nach spätestens 23 Sekunden beendet | 4 |
| `invalid_input` | Eingabe verletzt die Sicherheitsregeln | 64 |

Ein `401 Unauthorized` während des SIP-Digest-Handshakes ist normal, wenn danach
`registered` erreicht wird.

## 3. Eingehenden Testanruf prüfen

Unter **VoIP → Einstellungen** werden dieselben flüchtigen Zugangsdaten eingegeben und
**Eingehenden Anruf testen** gestartet. Danach muss innerhalb von 45 Sekunden die der
Nebenstelle zugewiesene Rufnummer angerufen werden. Der Harness:

1. registriert die Nebenstelle nur für dieses Testfenster,
2. nimmt genau einen eingehenden Anruf mit deaktiviertem Video und `audio=sendonly` an,
3. sendet ungefähr drei Sekunden lang einen neutralen 440-Hz-Testton,
4. legt automatisch auf und startet den dedizierten Sidecar neu.

Stabile Gate-2-Ergebnisse sind `incoming_answered`, `no_incoming_call`,
`caller_cancelled`, `answer_failed`, `auth_failed`, `registration_failed`, `timeout`,
`runtime_unavailable` und `busy`. Caller-ID, Peer-URI und Providerrohdaten verlassen den
Container nicht.

## 4. Cleanup

Nach Abschluss des Spikes:

```bash
incus delete --force hh-telephony-spike
```

Es werden weder Autostart noch ein dauerhaft öffentlicher Port eingerichtet.

## Scope

Gates 1 und 2 prüfen Registrierung sowie einen einzelnen eingehenden Anruf mit
sendonly-Testton. Dauerhafte Verbindungen, ausgehende Calls, bidirektionales RTP-Audio,
DTMF, HydraHive-Routing, STT/TTS und Produktinstallation folgen erst in getrennten Gates.
