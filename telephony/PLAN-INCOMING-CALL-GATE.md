# Plan: Gate 2 – eingehender FRITZ!Box-Testanruf

## Ziel

Das Telephony-Modul bietet einen authentifizierten, flüchtigen Eingangstest. Baresip
registriert sich im isolierten Sidecar, nimmt genau einen eingehenden Anruf mit
sendonly-Testton an, legt automatisch auf und hinterlässt weder Audio noch Credentials
oder Prozesse.

## Dateien

- `telephony/spike/ctrl_tcp.py` — begrenzter Netstring-/JSON-Client für Baresip
- `telephony/spike/incoming_probe.py` — Gate-2-State-Machine und stabile Ergebnisse
- `telephony/spike/stdin_payload.py` — gemeinsame strikt begrenzte stdin-Eingabe
- `telephony/spike/stdin_incoming_probe.py` — machine-only Gate-2-Einstieg
- `telephony/spike/run-stdin-incoming-probe.sh` — Container-Lock und Einstieg
- `telephony/spike/config.py` — eingehende Baresip-Konfiguration
- `telephony/spike/prepare-runtime.sh` — neue Runtime-Dateien verteilen
- `telephony/backend/probe_models.py` — Gate-2-Ergebniswerte
- `telephony/backend/probe_service.py` — Incoming-Prozessgrenze und Cleanup
- `telephony/backend/probe_routes.py` — authentifizierter Incoming-Endpoint
- `telephony/frontend/RegistrationProbeSettings.tsx` — Operatorflow
- `telephony/frontend/types.ts`, `i18n.ts`, `api.ts` — Vertrag und Texte
- `telephony/tests/test_ctrl_tcp.py` — Framing-/Limit-/JSON-Tests
- `telephony/tests/test_incoming_probe.py` — State-Machine-Tests
- `telephony/tests/test_stdin_incoming_probe.py` — stdin-/Secret-Vertrag
- bestehende Probe-/API-/Frontendtests — Regression und neuer Endpoint

## Implementierungsreihenfolge

### Task 1: Control-Protokoll und State Machine

- [ ] RED: fragmentierte/mehrfache Netstrings, Größenlimit und ungültiges JSON testen
- [ ] RED: Registrierung, Incoming, Accept, Established, Hangup und Fehlerpfade testen
- [ ] `ctrl_tcp.py` und `incoming_probe.py` minimal implementieren
- [ ] GREEN: Sidecar-Unit-Tests
- [ ] Commit: `feat(telephony): add incoming call sidecar probe`

### Task 2: Sichere stdin-/Runtime-Grenze

- [ ] RED: exakte Keys, Größenlimit, keine Secret-Ausgabe und feste Runtimepfade testen
- [ ] gemeinsame stdin-Validierung extrahieren
- [ ] Gate-2-stdin-Adapter und Lock-Script implementieren
- [ ] Runtime-Buildliste und Operatoranleitung aktualisieren
- [ ] GREEN: stdin- und bestehende Spike-Tests
- [ ] Commit zusammen mit Task 1, da beide dieselbe ausführbare Sidecar-Grenze bilden

### Task 3: Backend und API

- [ ] RED: 401, sanitisiertes 422, Rate-Limit und erlaubte Resultate testen
- [ ] RED: feste Args, stdin-only Credentials, gemeinsamer Lock, Timeout und Always-Cleanup
      testen
- [ ] Endpoint `POST /spike/incoming-test` und Servicepfad implementieren
- [ ] GREEN: API-/Service-Tests
- [ ] Commit: `feat(telephony): expose bounded incoming call test`

### Task 4: Frontend

- [ ] RED: separater Button, Jetzt-anrufen-Hinweis und keine Browserpersistenz testen
- [ ] API-/Typvertrag und deutsche/englische Texte ergänzen
- [ ] UI mit getrenntem Ladezustand und Passwort-Cleanup implementieren
- [ ] GREEN: Frontend-Vertragstest und echter installierter Produktionsbuild
- [ ] Commit: `feat(telephony): add incoming call settings flow`

### Task 5: Integration und Review

- [ ] lokalen Fake-SIP-Registrar um INVITE/ACK/BYE für einen echten Baresip-E2E erweitern
- [ ] Runtime-Dateien aktualisieren und Fake-SIP-E2E ausführen
- [ ] Timeout-/Container-Restart und rückstandsfreies Cleanup prüfen
- [ ] vollständige Telephony-Suite, Ruff, Shellsyntax und Frontend-Build
- [ ] Security-Audit und HH-Review
- [ ] Modulversion auf `0.4.0` erhöhen und Dokumentation aktualisieren
- [ ] Commit, Push, PR und CI

## Akzeptanzkriterien

- [ ] kontrollierte Annahme genau eines eingehenden Calls
- [ ] sendonly-Testton, kein eingehendes Audio und keine Aufnahme
- [ ] stabile, geheimnisfreie Ergebniswerte
- [ ] nur Loopback-Control-Port und private allowlistete SIP-Ziele
- [ ] gemeinsamer Lock verhindert parallele Registrierung/Calls
- [ ] harte Laufzeitgrenze und Runtime-Neustart nach jedem Versuch
- [ ] keine Prozess-, Tempdatei- oder Secret-Rückstände
- [ ] Tests und Builds grün

## Nicht in diesem Plan

- dauerhafter Gatewayprozess oder Credential Store
- Gate 3 (ausgehende Calls)
- vollständiges Gate 4 (bidirektionales RTP/DTMF)
- STT, TTS, Agentenlauf oder Gesprächsarchiv
