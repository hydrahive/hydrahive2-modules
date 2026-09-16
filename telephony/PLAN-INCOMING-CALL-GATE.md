# Plan: Gate 2 – eingehender FRITZ!Box-Testanruf

## Ziel

Das Telephony-Modul bietet einen authentifizierten, flüchtigen Eingangstest. Baresip
registriert sich im isolierten Sidecar, nimmt genau einen eingehenden Anruf mit
sendonly-Testton an, legt automatisch auf und hinterlässt weder Audio noch Credentials
oder Prozesse.

## Dateien

- `telephony/spike/ctrl_tcp.py` — begrenzter Netstring-/JSON-Client für Baresip
- `telephony/spike/incoming_probe.py` — Gate-2-State-Machine und stabile Ergebnisse
- `telephony/spike/incoming_runtime.py` — Baresip-Prozess- und Cleanup-Lifecycle
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

- [x] RED: fragmentierte/mehrfache Netstrings, Größenlimit und ungültiges JSON testen
- [x] RED: Registrierung, Incoming, Accept, Established, Hangup und Fehlerpfade testen
- [x] `ctrl_tcp.py` und `incoming_probe.py` minimal implementieren
- [x] GREEN: Sidecar-Unit-Tests
- [x] Commit: `feat(telephony): add incoming call sidecar probe`

### Task 2: Sichere stdin-/Runtime-Grenze

- [x] RED: exakte Keys, Größenlimit, keine Secret-Ausgabe und feste Runtimepfade testen
- [x] gemeinsame stdin-Validierung extrahieren
- [x] Gate-2-stdin-Adapter und Lock-Script implementieren
- [x] Runtime-Buildliste und Operatoranleitung aktualisieren
- [x] GREEN: stdin- und bestehende Spike-Tests
- [x] Commit zusammen mit Task 1, da beide dieselbe ausführbare Sidecar-Grenze bilden

### Task 3: Backend und API

- [x] RED: 401, sanitisiertes 422, Rate-Limit und erlaubte Resultate testen
- [x] RED: feste Args, stdin-only Credentials, gemeinsamer Lock, Timeout und Always-Cleanup
      testen
- [x] Endpoint `POST /spike/incoming-test` und Servicepfad implementieren
- [x] GREEN: API-/Service-Tests
- [x] Commit: `feat(telephony): expose bounded incoming call test`

### Task 4: Frontend

- [x] RED: separater Button, Jetzt-anrufen-Hinweis und keine Browserpersistenz testen
- [x] API-/Typvertrag und deutsche/englische Texte ergänzen
- [x] UI mit getrenntem Ladezustand und Passwort-Cleanup implementieren
- [x] GREEN: Frontend-Vertragstest und echter installierter Produktionsbuild
- [x] Commit: `feat(telephony): add incoming call settings flow`

### Task 5: Integration und Review

- [x] lokalen Fake-SIP-Registrar um INVITE/ACK/BYE für einen echten Baresip-E2E erweitern
- [x] Runtime-Dateien aktualisieren und Fake-SIP-E2E ausführen
- [x] Timeout-/Container-Restart und rückstandsfreies Cleanup prüfen
- [x] vollständige Telephony-Suite, Ruff, Shellsyntax und Frontend-Build
- [x] Security-Audit und HH-Review
- [x] Modulversion auf `0.4.1` erhöhen und Gate-2-TCP-Fix dokumentieren
- [x] Commit, Push, PR und CI

## Akzeptanzkriterien

- [x] kontrollierte Annahme genau eines eingehenden Calls
- [x] sendonly-Testton, kein eingehendes Audio und keine Aufnahme
- [x] stabile, geheimnisfreie Ergebniswerte
- [x] nur Loopback-Control-Port und private allowlistete SIP-Ziele
- [x] gemeinsamer Lock verhindert parallele Registrierung/Calls
- [x] harte Laufzeitgrenze und Runtime-Neustart nach jedem Versuch
- [x] keine Prozess-, Tempdatei- oder Secret-Rückstände
- [x] Tests und Builds grün

## Nicht in diesem Plan

- dauerhafter Gatewayprozess oder Credential Store
- Gate 3 (ausgehende Calls)
- vollständiges Gate 4 (bidirektionales RTP/DTMF)
- STT, TTS, Agentenlauf oder Gesprächsarchiv
