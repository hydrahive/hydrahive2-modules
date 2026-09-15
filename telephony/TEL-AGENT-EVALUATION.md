# Tel-Agent — gepinnte Evaluation und Lizenz-Gate

**Geprüfter Stand:** `Dpro-at/Tel-Agent@8a5193b2d801714e45ae6981a3506a60d562a99e`

**Prüfdatum:** 15. September 2026

**Upstream:** <https://github.com/Dpro-at/Tel-Agent>

Dieser Pin dokumentiert die technische Bewertung. Er ist keine Runtime-Abhängigkeit und
wird nicht automatisch heruntergeladen oder ausgeführt.

## Technischer Befund

Der Stand enthält nützliche, transportneutrale Konzepte:

- [`api/channels/phone.py`](https://github.com/Dpro-at/Tel-Agent/blob/8a5193b2d801714e45ae6981a3506a60d562a99e/api/channels/phone.py)
  trennt Call-/Archivlogik über ein kleines `CallTransport`-Protocol von Audio und SIP.
- [`agent/session/audio.py`](https://github.com/Dpro-at/Tel-Agent/blob/8a5193b2d801714e45ae6981a3506a60d562a99e/agent/session/audio.py)
  trennt Room-Audio, STT, TTS und Barge-in.
- Der Testansatz verwendet skriptbare Transporte statt Telefonprovider in Unit-Tests.

Der Stand beweist jedoch **keinen direkten FRITZ!Box-SIP-Betrieb**:

- [`CLAUDE.md`](https://github.com/Dpro-at/Tel-Agent/blob/8a5193b2d801714e45ae6981a3506a60d562a99e/CLAUDE.md#how-sip-is-handled-at-milestone-11--decided)
  entscheidet sich für LiveKit Cloud SIP und führt direkten SIP als verworfene Option.
- Die optionale Voice-Abhängigkeit in
  [`pyproject.toml`](https://github.com/Dpro-at/Tel-Agent/blob/8a5193b2d801714e45ae6981a3506a60d562a99e/pyproject.toml)
  enthält nur `livekit`; ein direkter SIP-Stack ist nicht deklariert.
- [`agent/session/livekit_room.py`](https://github.com/Dpro-at/Tel-Agent/blob/8a5193b2d801714e45ae6981a3506a60d562a99e/agent/session/livekit_room.py)
  bezeichnet den LiveKit-Raumpfad ausdrücklich als nicht auf einer realen Leitung bewiesen.
- [`api/system/status.py`](https://github.com/Dpro-at/Tel-Agent/blob/8a5193b2d801714e45ae6981a3506a60d562a99e/api/system/status.py)
  führt `sip`, `stt` und `tts` weiterhin als `UNBUILT`.

Die README-Aussage zur SIP-/LiveKit-Telefonie reicht daher nicht als HydraHive-Release-
Nachweis. Maßgeblich sind ausführbarer Code und ein eigener echter E2E-Test.

## Entscheidung für HydraHive

1. Tel-Agent bleibt Referenz und möglicher späterer Sidecar-Baustein.
2. In HydraHive wird kein Tel-Agent-Code kopiert oder importiert.
3. Der Gatewayvertrag bleibt unabhängig von dessen Datenbank, API, Benutzerverwaltung,
   Tools und Dashboard.
4. Vor einer Runtime-Integration muss der FRITZ!Box-Spike den Transportweg entscheiden.
5. Der Upstream-Pin wird bei einer Neubewertung bewusst aktualisiert; kein stilles
   `latest` ist erlaubt.

## Lizenz-Gate

Der gepinnte Stand deklariert in `pyproject.toml` **AGPL-3.0-or-later** und enthält die
GNU Affero General Public License v3. Daraus folgen für eine mögliche Nutzung mindestens
diese betrieblichen Gates:

- Tel-Agent ausschließlich als klar separaten Prozess/Container behandeln;
- Copyright-, Lizenz- und Quellcodehinweise erhalten;
- Änderungen an einem eingesetzten AGPL-Sidecar nachvollziehbar führen;
- den korrespondierenden Quellcode einer eingesetzten modifizierten Netzwerkversion für
  deren Nutzer gemäß AGPL bereitstellen;
- Distributionsartefakte, Buildskripte und Notices vor Veröffentlichung prüfen;
- vor Produktdistribution eine qualifizierte Lizenzprüfung durchführen.

Die Prozess-/API-Grenze allein ist keine pauschale Aussage zur Lizenzkompatibilität. Diese
Notiz ist eine Engineering-Gate-Liste und keine Rechtsberatung.

## Erneute Bewertung auslösen, wenn

- Upstream einen tatsächlich ausführbaren direkten SIP-Adapter ergänzt;
- ein reproduzierbarer LiveKit-SIP-E2E-Nachweis veröffentlicht wird;
- HydraHive den Sidecar verändern oder mit ausliefern möchte;
- Lizenzangaben, Ownership oder Distributionsform des Upstreams wechseln.
