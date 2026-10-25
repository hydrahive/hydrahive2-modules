# Plan: VoIP Etappe 2a – Anrufe annehmen, Ansage, Testanruf

Auftrag Till, 25.10.2026: Etappe 2 in zwei Schritten. Zuerst 2a (abnehmen, Ansage, Testanruf), danach 2b mit dem
Ziel „C“: Der Telefon-Agent nimmt Anliegen auf **und** beantwortet Fragen. Anrufer sind Fremde und bekommen nur kleine
Rechte. Später kommt die Anbindung an einen Kontaktmanager (eigener Task, noch zu planen).

## Ausgangslage (geprüft)

- Die Anmeldung an der FRITZ!Box 6591 läuft (0.6.1, .2 über WLAN 192.168.3.29).
- INVITE von 192.168.3.1:5060 kommt an und wird heute mit 480 abgelehnt.
- Auf der .2 laufen Piper (TTS, 127.0.0.1:10200, Wyoming) und Whisper (STT, :10300). Dort läuft Python 3.14,
  `audioop` gibt es nicht mehr → G.711 wird selbst kodiert (A-law/µ-law, je ~20 Zeilen, Tests gegen ITU-Tabelle).
- Das Tonformat der FRITZ!Box ist noch nicht mitgeschnitten. Deshalb werden PCMA (8) **und** PCMU (0) angenommen,
  maßgeblich ist die Reihenfolge des Angebots der FRITZ!Box.

## Ziel

1. Schalter **„Anrufe annehmen“** (Standard **aus**) und **Ansagetext** in den Einstellungen.
2. Schalter an → HydraHive nimmt ab, spielt die Ansage (lokales Piper, sonst ein eingebauter Hinweiston) und legt auf.
3. Schalter aus → wie bisher 480 (die anderen Telefone der Rufnummer klingeln weiter).
4. Knopf **„Testanruf starten“**: Ein Fenster von 60 s nimmt genau einen Anruf an, auch wenn der Schalter aus ist.
   Danach fragt die Seite: „Ton gehört? Ja / Nein“. Das Ergebnis wird angezeigt und gespeichert.
5. **Letzter Anruf** wird angezeigt: Zeit, Rufnummer (maskiert bis auf die letzten 3 Ziffern), Ergebnis
   (angenommen / abgelehnt / vom Anrufer beendet) und ob Ton vom Anrufer ankam (nur Paketzähler).

## Ablauf eines Anrufs (RFC 3261 / 3264 / 3550)

INVITE (nur von der Anlage, IP **und** Port) → `100 Trying` → `180 Ringing` → kurze Pause (1 s) → `200 OK` mit SDP
(eigene Adresse wie im Contact, ein RTP-Port aus dem Sprach-Bereich, gewählter Codec, `a=sendrecv`, `a=ptime:20`)
→ warten auf ACK (`200 OK` wird nach T1 verdoppelnd wiederholt, höchstens 32 s) → Ansage als RTP (20 ms, 160 Byte,
Zeitstempel/Sequenz/SSRC korrekt) → 0,5 s Stille → `BYE` → `200 OK` auf BYE.

Sonderfälle:
- **CANCEL** vor dem Abnehmen → `200 OK` auf CANCEL, `487 Request Terminated` auf INVITE.
- **BYE vom Anrufer** während der Ansage → `200 OK`, Wiedergabe sofort stoppen.
- Zweiter INVITE während eines Anrufs → `486 Busy Here`.
- Erneuter INVITE desselben Anrufs (Wiederholung) → letzte Antwort wiederholen, kein zweiter Anruf.
- re-INVITE im Gespräch → `488 Not Acceptable Here` (Etappe 2a hält es einfach).
- Kein gemeinsamer Codec → `488 Not Acceptable Here`.
- Höchstdauer je Anruf: 60 s, danach BYE.
- **Ton vom Anrufer** wird nur gezählt (Pakete) und **nie gespeichert oder ausgewertet**. RTP von anderen Adressen
  als der aus dem SDP der Anlage wird verworfen.

## Dateien

- `migrations/002_calls.sql` – Spalten `answer_calls`, `greeting` an der Verbindung; Tabelle `module_telephony_calls`
  (Zeit, maskierte Nummer, Ergebnis, Codec, Pakete hin/zurück, Test-Bestätigung). Höchstens 50 Einträge je Verbindung.
- `backend/sip/sdp.py` – Angebot lesen (Adresse, Port, Codecs), Antwort bauen
- `backend/media/g711.py` – PCM16 → A-law/µ-law
- `backend/media/rtp.py` – RTP-Pakete bauen/lesen, Sender mit 20-ms-Takt, Zähler für Eingang
- `backend/media/greeting.py` – Ansage: Piper (Wyoming) → PCM16 → auf 8 kHz bringen → G.711, mit Zwischenspeicher je
  Text. Fällt Piper aus: eingebauter Hinweiston.
- `backend/sip/call.py` – ein Anruf als Zustandsmaschine (wartet auf ACK, spielt, legt auf), unabhängig testbar
- `backend/sip/agent.py` – INVITE/ACK/BYE/CANCEL an den laufenden Anruf weiterreichen (Datei bleibt < 200 Zeilen,
  Anruflogik liegt in `call.py`)
- `backend/calls.py` + Routen: Testfenster öffnen, Ergebnis bestätigen, letzte Anrufe
- Frontend: Schalter, Ansagetext, Testanruf-Karte, Anrufliste (Einstellungen), Texte DE/EN
- Tests: echter SIP-„Anrufer“ im Test (INVITE mit SDP, ACK, RTP-Empfang zählen, BYE/CANCEL), G.711 gegen Tabelle

## Reihenfolge (TDD: rot → grün → Mutantenprobe)

1. G.711-Kodierung
2. SDP lesen/bauen
3. RTP bauen/Sender (Takt, Sequenz, Zeitstempel)
4. Ansage (Piper-Anbindung mit Fake-Wyoming-Server im Test; Fallback-Ton)
5. Anruf-Zustandsmaschine gegen Test-Anrufer (normal, CANCEL, BYE vom Anrufer, Busy, Codec-Fehler, Wiederholung,
   fremde RTP-Quelle)
6. Agent: Weitergabe, Schalter aus = 480 wie bisher
7. Speicher + API (Schalter, Ansage, Testfenster, Bestätigung, Liste) – nur eigene Verbindung
8. Oberfläche + Texte
9. Live: echter Anruf auf der .2, Mitschnitt nur der Steuernachrichten, Till bestätigt „Ton gehört“

## Akzeptanzkriterien

- Echter Anruf über die FRITZ!Box: Till hört die Ansage, danach legt HydraHive auf
- Testanruf mit „Ton gehört“ funktioniert und wird angezeigt
- Schalter aus → Verhalten wie 0.6.1
- Kein Ton des Anrufers wird gespeichert; Rufnummern nur maskiert
- Volle Modul-Suite, ruff, tsc/eslint/vitest grün; Mutantenprobe

## Nicht in 2a

- Zuhören und Antworten (Whisper/Agent) → 2b
- Ausgehende Anrufe → Etappe 3
- Kontaktmanager, Archiv, Projekte/Mitglieder → später
