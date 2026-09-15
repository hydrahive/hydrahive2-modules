# Plan: Telefonie-Gatewayvertrag und deterministischer Fake

## Ziel

HydraHive erhält einen transportneutralen, typisierten Kontroll- und Ereignisvertrag für
Telefonie-Gateways. Ein deterministischer In-Process-Fake beweist Zustände,
Projekt-/Verbindungsbindung, Ereignisreihenfolge und Idempotenz, ohne SIP, RTP,
Netzwerkzugriff oder echte Zugangsdaten zu verwenden.

## Designentscheidung

Drei Ansätze wurden bewertet:

1. **Tel-Agent direkt adaptieren:** derzeit ungeeignet, weil der gepinnte Stand keinen
   nachgewiesenen direkten FRITZ!Box-SIP-Transport bereitstellt und der LiveKit-Pfad sich
   selbst als nicht real verifiziert kennzeichnet.
2. **HTTP-/WebSocket-Wireformat sofort festschreiben:** verfrüht, solange Maschinenauth,
   Deployment und der reale Transport noch nicht durch den Spike entschieden sind.
3. **Reiner Python-Port plus typisierte Modelle und Fake:** gewählt. Fachsemantik und
   Sicherheitsgrenzen werden jetzt festgelegt; Serialisierung und Transport folgen nach
   dem Hardware-Spike als Adapter, ohne Aufrufer umzubauen.

Trade-off: Diese Etappe ermöglicht noch keinen echten Anruf und erweitert den öffentlichen
API-Status bewusst nicht um verfügbare Telefoniefunktionen.

## Dateien

- `telephony/backend/gateway/models.py` — strikte, unveränderliche Connection-, Call-,
  Command-, Health- und Eventmodelle; Zugangsdaten über `SecretStr`
- `telephony/backend/gateway/protocol.py` — asynchroner `TelephonyGateway`-Port und
  redaktionssichere Fehlercodes
- `telephony/backend/gateway/fake.py` — deterministische Zustandsmaschine und Eventqueue
- `telephony/backend/gateway/__init__.py` — kleine öffentliche Importfläche
- `telephony/tests/test_gateway_contract.py` — Contract-, Idempotenz-, Sequenz-,
  Isolation- und Redaction-Tests
- `telephony/GATEWAY-CONTRACT.md` — verbindliche Semantik und spätere Wire-Grenzen
- `telephony/TEL-AGENT-EVALUATION.md` — gepinnter Upstream, Lizenz- und Reifegrad-Gate
- `telephony/FRITZBOX-SPIKE.md` — sicherer echter Testplan und Abnahmekriterien
- `telephony/manifest.json` — Minor-Version `0.2.0`
- `telephony/PLAN-V1.md` — erledigte Gate-Schritte markieren
- `README.md`, `README.de.md` — Katalogversion und Contribution aktualisieren

## Implementierungsreihenfolge

### Task 1: Vertrag und Fake

- [x] RED: Tests für Secret-Redaction, strikte Eingaben, Protocol-Kompatibilität,
  idempotentes Dialing, Attempt-Konflikte, Projektisolation und monotone Events schreiben
- [x] Tests ausführen und fehlende Gateway-Module bestätigen
- [x] Modelle, Protocol und minimalen Fake implementieren
- [x] Tests grün ausführen
- [x] Manifest und Katalog auf `0.2.0` aktualisieren
- [x] Commit: `feat(telephony): define gateway contract and fake`

### Task 2: Lizenz-, Upstream- und Hardware-Gate dokumentieren

- [x] Tel-Agent auf Commit `8a5193b2d801714e45ae6981a3506a60d562a99e` pinnen
- [x] AGPL-/Sidecar-Grenzen und verpflichtende Rechtsprüfung dokumentieren
- [x] Reifegrad anhand des gepinnten Quellstands belegen
- [x] sicheren FRITZ!Box-Spike ohne reale Secrets dokumentieren
- [x] erledigte Punkte in `PLAN-V1.md` markieren
- [x] Commit: `docs(telephony): record transport and licence gates`

## Akzeptanzkriterien

- [x] Fake erfüllt den runtime-checkbaren Gateway-Port
- [x] gleiche `attempt_id` plus identischer Auftrag erzeugt nur einen Call und ein
  `dialing`-Ereignis
- [x] Wiederverwendung einer `attempt_id` für einen anderen Auftrag wird abgewiesen
- [x] fremde Projekt-/Verbindungsreferenzen können keinen Call steuern
- [x] Ereignisse sind pro Call streng monoton und tragen alle Pflichtidentitäten
- [x] Credentials erscheinen weder in `repr` noch JSON-Ausgaben
- [x] kein Produktionscode öffnet Ports, führt Netzwerkzugriffe aus oder behauptet
  verfügbare Telefonie
- [x] Tel-Agent-Stand, Lizenzgrenze und echter Spike sind reproduzierbar dokumentiert

## Nicht in diesem Plan

- öffentlicher Setup- oder Gateway-API-Endpunkt
- HTTP-/WebSocket-Client und Maschinenauthentifizierung
- Persistenz, Migrationen, Projektanlage oder Secret-Store
- SIP-Registrierung, RTP, STT/TTS oder echter Telefonanruf
- Installation oder Ausführung von Tel-Agent, Asterisk, FreeSWITCH oder LiveKit
