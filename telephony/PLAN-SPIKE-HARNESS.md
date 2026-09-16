# Plan: Sicherer FRITZ!Box-Registrierungs-Spike

## Ziel

Ein reproduzierbarer, isolierter Developer-Harness prüft Gate 1 des FRITZ!Box-Spikes:
Baresip 4.11.0 registriert eine dedizierte IP-Telefon-Nebenstelle über das lokale Netz.
Benutzername und Passwort werden verdeckt interaktiv eingelesen, nur in einem temporären
Verzeichnis verarbeitet und nie als Argument, Environment, Log oder Workspace-Datei
persistiert.

## Optionen und Entscheidung

1. **pyVoIP 1.6.8:** einfache Python-Integration, aber stabile Veröffentlichung von Januar
   2024, viele offene Issues und GPL-3.0. Für einen dauerhaft eingebetteten Adapter keine
   gute erste Wahl.
2. **PJSIP/PJSUA2:** reif, aber GPL-2.0 beziehungsweise kommerzielle Lizenz und komplexer
   nativer Python-Build.
3. **Baresip 4.11.0 als isolierter Prozess:** aktiv gepflegt, BSD-3-Clause, modular,
   G.711/RTP und headless Control vorhanden. Gewählt für den Spike.

Das Ubuntu-Paket 1.1.0 wird nicht verwendet: es liegt weit hinter dem geprüften Release
4.11.0 und vor aktuellen `libre`-Security-Fixes.

## Dateien

- `telephony/spike/config.py` — private IPv4-, Username- und Credentialvalidierung sowie
  minimale Baresip-Konfiguration ohne Secret-Ausgabe
- `telephony/spike/probe.py` — zeitbegrenzter Registrierungsprozess und stabile Ergebnis-
  codes; rohe Providerlogs bleiben unterdrückt
- `telephony/spike/cli.py` — verdeckte interaktive Eingabe, keine Secret-Argumente
- `telephony/spike/prepare-runtime.sh` — isolierter Incus-Build mit gepinnten Baresip-/
  libre-Commits; überschreibt keine bestehenden Container
- `telephony/spike/README.md` — Operatorablauf, Cleanup und Grenzen
- `telephony/tests/test_spike_config.py` — Injection-, Redaction- und Dateimodus-Tests
- `telephony/tests/test_spike_probe.py` — Parser-, Timeout- und Kommandovertrags-Tests
- `telephony/manifest.json` — Patch-Version `0.2.1`

## TDD-Reihenfolge

1. [x] RED: Eingabevalidierung und Config-Injection-Tests
2. [x] RED: Secret-Redaction in Repr, Fehlern und Ausgabe
3. [x] RED: Erfolgs-/Fehler-/Timeoutparser mit Fake-Baresip-Prozess
4. [x] Minimalen Config-Renderer und Probe-Runner implementieren
5. [x] CLI mit `getpass`, ohne Passwortargument/-environment implementieren
6. [x] gepinnten Incus-Runtime-Build und Operatoranleitung ergänzen
7. [x] Tests, Ruff, Shell-Syntax und Versionsguard grün
8. [x] Commit und Review-PR erstellen
9. [ ] Echten Registrierungsprobe interaktiv mit Betreiber-Credentials ausführen

## Akzeptanzkriterien

- [x] nur private IPv4-Registrarziele sind zulässig
- [x] CR/LF, Semikolon und Account-Parameter-Injection werden verworfen
- [x] Credentials erscheinen nicht in `repr`, Exceptions, JSON oder Prozessargumenten
- [x] Config-/Accountdateien erhalten Modus `0600` und werden nach jedem Lauf entfernt
- [x] SIP-Trace und Verbose-Logging bleiben aus
- [x] der Prozess endet nach spätestens 30 Sekunden
- [x] Ausgabe besteht nur aus stabilen Codes wie `registered`, `auth_failed`,
  `registration_failed` oder `timeout`
- [x] Runtime ist auf Baresip/libre 4.11.0 und konkrete Commits gepinnt
- [x] kein bestehender Incus-Container wird überschrieben

## Nicht enthalten

- automatische FRITZ!Box-Konfiguration
- Übergabe von Zugangsdaten über Chat oder HydraHive-API
- eingehende/ausgehende Calls und Audio-Gates 2–4
- Produktinstallation, Autostart oder öffentlicher Netzwerkdienst
