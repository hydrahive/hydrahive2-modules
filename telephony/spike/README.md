# FRITZ!Box SIP Spike Harness

Dieser Ordner ist ein isoliertes Developer-Werkzeug für Gate 1 des Telefonie-Spikes. Er
ist **kein** Teil der installierten Produktions-Runtime. Der Harness baut Baresip 4.11.0
und libre 4.11.0 in einem separaten, unprivilegierten Incus-Container und prüft genau
eine SIP-Registrierung per UDP/G.711.

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

## 1. Runtime einmalig vorbereiten

Im Repository `hydrahive2-modules`:

```bash
chmod +x telephony/spike/prepare-runtime.sh telephony/spike/run-probe.sh
./telephony/spike/prepare-runtime.sh
```

Der Build ist auf diese Releases und Commits gepinnt:

- Baresip 4.11.0: `3d30821f099925d24167f8a99e93ba4d1be98599`
- libre 4.11.0: `ceefe9ff499aa1bcfb6255aff1737434dd385322`

Das veraltete Ubuntu-Baresip-Paket wird nicht installiert.

## 2. Registrierung interaktiv prüfen

```bash
incus exec hh-telephony-spike -- \
  /opt/hh-telephony-spike/spike/run-probe.sh \
  --registrar 192.168.3.1
```

Beide Eingaben bleiben unsichtbar. Erlaubt sind beim Benutzernamen 8–64 Zeichen
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

## 3. Cleanup

Nach Abschluss des Spikes:

```bash
incus delete --force hh-telephony-spike
```

Es werden weder Autostart noch ein dauerhaft öffentlicher Port eingerichtet.

## Scope

Aktuell wird nur Gate 1 (Registrierung) geprüft. Eingehende und ausgehende Calls,
RTP-Audio, DTMF, Hydrahive-Routing sowie Produktinstallation folgen erst nach einem
erfolgreichen Gate 1 und separater Freigabe.
