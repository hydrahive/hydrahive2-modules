# Plan: FRITZ!Box-Registrierungstest in den VoIP-Einstellungen

## Ziel

Ein authentifizierter Benutzer kann Gate 1 des FRITZ!Box-Spikes vollständig über
**VoIP → Einstellungen** ausführen. Credentials bleiben flüchtig; Backend und Sidecar
geben ausschließlich stabile Ergebniswerte zurück.

## Dateien

- `telephony/backend/probe_models.py` — strikte Request-/Response-Modelle
- `telephony/backend/probe_service.py` — fester Incus-Prozessvertrag, globales
  Parallelitätsgate und Output-Sanitizing
- `telephony/backend/probe_routes.py` — Auth, Rate-Limit und sanitizierte API-Fehler
- `telephony/backend/__init__.py` — Probe-Router registrieren
- `telephony/spike/stdin_probe.py` — begrenzter Secret-Transport über stdin
- `telephony/spike/prepare-runtime.sh` — neuen Runner in den Sidecar kopieren
- `telephony/frontend/RegistrationProbeSettings.tsx` — sicheres Formular und Ergebnis-UI
- `telephony/frontend/api.ts` — Probe-API
- `telephony/frontend/types.ts` — Probe-Typen
- `telephony/frontend/VoIPPage.tsx` — Einstellungsabschnitt verdrahten
- `telephony/frontend/i18n.ts` — deutsche und englische Texte
- `telephony/tests/test_probe_api.py` — Auth, Validation, Rate-Limit und Sanitizing
- `telephony/tests/test_probe_service.py` — Args/Env/stdin, Timeout, Lock und Outputparser
- `telephony/tests/test_stdin_probe.py` — stdin-Größe, Feldvertrag und stabile Ausgabe
- `telephony/tests/test_settings_frontend.py` — kein Browser-Storage und korrekte Verdrahtung
- `telephony/manifest.json` / Foundation-Test — Minor-Version `0.3.0`

## Implementierungsreihenfolge

### Task 1: API-Vertrag

- [x] Request-/Response- und Route-Tests schreiben
- [x] RED für Auth, private IPv4, `extra=forbid`, Secret-Echo und Rate-Limit bestätigen
- [x] Modelle und Route minimal implementieren
- [x] Tests grün

### Task 2: Sicherer Prozessadapter

- [x] Tests für feste Args, leeres Secret-Environment, stdin-Übertragung, Lock und Timeout
      schreiben
- [x] RED bestätigen
- [x] `probe_service.py` mit `shell=False`, hartem Timeout und Ergebnis-Allowlist bauen
- [x] Tests grün

### Task 3: Container-stdin-Runner

- [x] Tests für Größenlimit, exakte Keys, ungültige Eingaben und Erfolgsstatus schreiben
- [x] RED bestätigen
- [x] `stdin_probe.py` implementieren und im Runtime-Build verteilen
- [x] gegen die bestehende isolierte Baresip-Runtime testen

### Task 4: Einstellungsoberfläche

- [x] Frontend-Vertragstest für Settings-Rendering, Passwortfeld, API-Aufruf und fehlende
      Browser-Persistenz schreiben
- [x] RED bestätigen
- [x] Formular, Typen, API und i18n implementieren
- [x] TypeScript-/Produktionsbuild grün

### Task 5: Abschluss

- [x] Manifest auf `0.3.0` erhöhen
- [x] vollständige Telephony-Suite und Ruff ausführen
- [x] Security-Audit und HH-Review durchführen
- [x] Sidecar-Dummyregistrierung, authentifizierten API-E2E und Frontend-Build ohne reale
      Credentials prüfen
- [ ] Commit, PR aktualisieren und CI abwarten

## Akzeptanzkriterien

Die verbindlichen Kriterien stehen in
`telephony/SPEC-SETTINGS-PROBE.md` und müssen vollständig grün sein.

## Nicht in diesem Plan

- dauerhafte Credential-Ablage
- Projekt-/Agent-Erzeugung
- Calls oder Audio-Gates
