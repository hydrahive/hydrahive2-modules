# Plan: Gate 2 – RTP-Senden und Hörbarkeit getrennt verifizieren

## Ziel

Der Eingangstest darf `CALL_ESTABLISHED` nicht länger als Beweis für einen hörbaren
Testton darstellen. Nach der Annahme prüft die Sidecar-State-Machine zusätzlich die
von Baresip gemeldeten RTP-TX-Paket- und Bytezähler. Die UI erklärt Gate 2 erst nach
positiver RTP-TX-Prüfung **und** expliziter Hörbestätigung durch den Operator für
bestanden.

## Entscheidung

### Gewählter Ansatz: `audio_debug`-Zähler plus manuelle Hörbestätigung

- Baresip liefert über den bereits loopbackgebundenen `ctrl_tcp`-Kanal aggregierte
  RTP-TX-Paket- und Bytezähler.
- Nur positive Paket- **und** Bytezähler gelten als technischer Mediennachweis.
- Hörbarkeit kann technisch nicht bis hinter FRITZ!Box und Telefon bewiesen werden;
  deshalb bestätigt der Operator den gehörten Ton ausdrücklich in der UI.
- Rohes RTP, Audio, SDP, Call-IDs und Gegenstellen werden weder zurückgegeben noch
  persistiert.

### Verworfene Alternativen

- Paketmitschnitt: stärkerer Netzwerkbeweis, aber unnötige Root-/Capture-Rechte und
  höheres Datenschutzrisiko.
- `CALL_ESTABLISHED` beibehalten: beweist nur SIP-Signalisierung und erzeugt den
  bereits beobachteten falschen Erfolg.
- Reine Hörbestätigung: erkennt nicht, ob Baresip überhaupt RTP erzeugt hat.

## Dateien

- `telephony/spike/incoming_probe.py` — `audio_debug` abfragen, RTP-TX-Zähler sicher
  parsen, `media_failed` ausgeben und immer kontrolliert auflegen
- `telephony/spike/incoming_runtime.py` — vier Sekunden messbares Testaudio erzeugen
- `telephony/backend/probe_models.py` — stabilen `media_failed`-Outcome ergänzen
- `telephony/frontend/types.ts` — Outcome-Vertrag ergänzen
- `telephony/frontend/RegistrationProbeSettings.tsx`, `ProbeResult.tsx` — technische
  Medienprüfung und menschliche Hörbestätigung getrennt darstellen
- `telephony/frontend/i18n.ts` — ehrliche deutsche/englische Ergebnis- und
  Bestätigungstexte
- `telephony/manifest.json` — Modulversion erhöhen
- `telephony/tests/` — State-Machine-, Backend-, API- und Frontend-Vertragstests

## Implementierungsreihenfolge

### Task 1: Technischen Mediennachweis TDD-gesichert ergänzen

- [x] RED: etablierter Call mit positiven `TX: packets=…, octets=…`-Zählern ist
      technisch erfolgreich
- [x] RED: null, fehlende, fehlerhafte oder ausbleibende `audio_debug`-Antwort ergibt
      `media_failed`
- [x] RED: bei Medienfehler wird trotzdem genau dieser Call aufgelegt
- [x] Minimalimplementierung in `incoming_probe.py`
- [x] Messfenster auf vier Sekunden setzen; Paket- und Bytezähler sind ohne das
      verzögerte Bitratenintervall unmittelbar belastbar
- [x] GREEN: vollständige Sidecar-Tests

### Task 2: Outcome durch Backend und API führen

- [x] RED: `media_failed` ist ein erlaubter, geheimnisfreier API-Outcome
- [x] Backend-Enum und Verträge ergänzen
- [x] GREEN: Service- und API-Tests

### Task 3: Hörbestätigung in der UI

- [x] RED: `incoming_answered` ist ohne Bestätigung kein grüner Gate-Erfolg
- [x] RED: „Ton gehört“ zeigt Gate 2 als bestanden
- [x] RED: „Kein Ton“ hält Gate 2 offen und erklärt den Medienpfadfehler
- [x] UI-State und deutsche/englische Texte implementieren
- [x] GREEN: Frontend-Vertragstests und Produktionsbuild

### Task 4: Integration und Abschluss

- [x] Fake-SIP-E2E weist positive RTP-TX-Paket-/Bytezähler, 199 variierende
      G.711-Audiopakete und BYE nach
- [x] vollständige Telephony-Suite, Ruff, Build, Security-Audit und HH-Review
- [ ] Modulversion erhöhen, Commit, PR, CI und Runtime-Sync
- [ ] genau ein frischer FRITZ!Box-Test; Gate 2 nur nach gehörter Tonbestätigung schließen

## Akzeptanzkriterien

- [x] `CALL_ESTABLISHED` allein erzeugt keine Gate-bestanden-Meldung
- [x] positive Baresip-RTP-TX-Paket- und Bytezähler werden vor dem Auflegen nachgewiesen
- [x] fehlende oder Null-TX-Zähler liefern `media_failed`
- [x] Operator kann „Ton gehört“ oder „kein Ton“ eindeutig bestätigen
- [x] Gate 2 wird nur bei technischem Mediennachweis plus „Ton gehört“ grün
- [x] keine Audio-, RTP-, SDP-, Call-ID-, Caller- oder Credential-Persistenz
- [x] Cleanup und Ein-Anruf-Grenze bleiben unverändert

## Nicht in diesem Plan

- eingehendes Audio, Aufnahme oder STT
- privilegierter Paketmitschnitt
- dauerhafte Speicherung der Hörbestätigung
- Gate 3/4, TTS oder Agentengespräche
