# FRITZ!Box-SIP-Spike — sicheres Realtest-Runbook

**Status:** vorbereitet, noch nicht ausgeführt

## Ziel

Vor jedem Produktversprechen wird bewiesen, dass ein isolierter lokaler Gateway eine
dedizierte FRITZ!Box-IP-Telefon-Nebenstelle registrieren, einen echten Anruf annehmen und
Audio in beide Richtungen transportieren kann. Der Test entscheidet den Transportadapter;
er testet noch nicht den vollständigen Telefon-Agenten.

## Voraussetzungen durch den Betreiber

- FRITZ!Box im selben vertrauenswürdigen LAN wie der isolierte Testhost
- neu angelegte, ausschließlich für den Spike bestimmte IP-Telefon-Nebenstelle
- starkes, einmaliges SIP-Passwort
- ausgehende Berechtigung zunächst deaktiviert oder auf eine eigene Testnummer begrenzt
- eine eigene Mobil-/Festnetznummer für kontrollierte Testanrufe
- ausdrückliche Zustimmung aller Testteilnehmer zu Audio und Testprotokollierung

Produktive Hauptzugänge, Notrufziele, Premium-/Mehrwertnummern und fremde Personen sind
für den Spike ausgeschlossen.

## Secret-Hygiene

Bis der projektbezogene Secret-Store existiert, werden FRITZ!Box-Zugangsdaten **nicht**
in HydraHive gespeichert. Ein Spike-Harness muss sie interaktiv über eine verdeckte
Eingabe oder einen kurzlebigen, geschützten Secret-Mechanismus erhalten.

Verboten sind:

- Repository-, Workspace-, Markdown-, `.env`- oder Shell-History-Einträge;
- Kommandozeilenargumente mit Benutzername oder Passwort;
- SIP-Debuglogs mit `Authorization`-/Digest-Inhalten;
- Screenshots oder Anhänge mit Zugangsdaten.

Nach dem Test wird die Nebenstelle deaktiviert oder ihr Passwort rotiert.

## Kandidatenreihenfolge

1. **Direkter lokaler SIP-Adapter**, wenn Registrierung, RTP, Codec und sofortiges
   Playback-Abbrechen zuverlässig implementierbar sind.
2. **Lokaler Asterisk-/FreeSWITCH-Adapter** als PBX-Brücke, wenn direkter SIP unnötig
   riskant oder instabil ist.
3. **LiveKit-SIP** nur als eigener Provider-/Cloud-Pfad; er beweist nicht den geforderten
   lokalen FRITZ!Box-LAN-Pfad und ist daher kein Ersatz für diesen Spike.

Jeder Kandidat muss denselben HydraHive-Gatewayvertrag implementieren. Fachmodell und UI
dürfen durch die Transportwahl nicht verändert werden.

## Testfolge

### Gate 1: Netzwerk und Registrierung

- Registrar nur über die lokale Ziel-Allowlist erreichen
- SIP `REGISTER` mit der dedizierten Nebenstelle
- erfolgreichen Status und kontrollierten Re-Register beobachten
- falsches Passwort liefert nur `auth_failed`, keine Providerdetails oder Secrets
- Pausieren beendet die Registrierung sauber

### Gate 2: Eingehender Ruf

- eigene Testnummer ruft die zugeordnete FRITZ!Box-Rufnummer an
- Gateway beobachtet `incoming` mit korrekter Projekt-/Verbindungsreferenz
- Annehmen beendet das Klingeln
- lokaler Hardcoded-Ton oder Begrüßung ist am Telefon hörbar
- gesprochenes Testaudio erreicht den Gateway
- Auflegen auf beiden Seiten erzeugt genau einen terminalen Zustand

### Gate 3: Audio und Unterbrechung

- Audio läuft mindestens 60 Sekunden stabil in beide Richtungen
- ausgegebene Audiodaten können sofort gestoppt und aus der Queue entfernt werden
- Paketverlust/Jitter werden gemessen, nicht kaschiert
- Codec, Sample-Rate und notwendiges Resampling werden protokolliert

### Gate 4: Kontrollierter ausgehender Ruf

Erst nach bewusst aktivierter Ausgangsberechtigung:

- exakt die eigene allowlistete Testnummer wählen
- dieselbe `attempt_id` doppelt senden und genau einen realen Ruf nachweisen
- Klingeln, Annehmen, beidseitiges Audio und Auflegen prüfen
- Busy, No-answer und Ablehnung getrennt beobachten

## Abnahmekriterien

Der lokale Transportkandidat ist nur bestanden, wenn:

- Registrierung und Re-Register mindestens 30 Minuten stabil bleiben;
- je drei eingehende und ausgehende Testanrufe ohne Doppelruf funktionieren;
- Audio in beide Richtungen verständlich ist;
- Barge-in-Ausgabe innerhalb von 250 ms stoppt;
- Ereignisse pro Call lückenlos und monoton sind;
- Projekt-/Verbindungs-Mismatches abgewiesen werden;
- Logs und gespeicherte Artefakte keine Credentials enthalten;
- keine FRITZ!Box-, SIP- oder Gateway-Schnittstelle aus dem Internet erreichbar ist.

Erst danach folgen STT/LLM/TTS-Messungen. Für das spätere V1-Ziel werden mindestens 20
reale, einvernehmliche Testcalls mit End-of-speech-bis-first-audio-Messung benötigt; über
1,5 Sekunden wird zuerst Streaming/Endpointing verbessert.

## Ergebnisprotokoll

Das Protokoll enthält ausschließlich:

- Datum, Hardware-/Softwareversion und Adapter-Commit
- bestandene/fehlgeschlagene Gates
- redigierte Fehlercodes
- Codec, Latenz-, Jitter- und Paketverlustwerte
- Entscheidung `direct`, `local_pbx` oder `rejected`

Rufnummern werden maskiert, Gesprächsinhalte nicht aufgenommen und Zugangsdaten niemals
übernommen. Ein fehlgeschlagener Spike ist ein gültiges Ergebnis und stoppt die
Produktbehauptung „FRITZ!Box-kompatibel“.
