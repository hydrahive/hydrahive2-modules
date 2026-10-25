# Plan: VoIP Etappe 3 – HydraHive ruft selbst an

Auftrag Till, 25.10.2026: „nun Etappe 3“. Vorschlag (von Till freigegeben): Anrufen per Knopf, **nur durch den
Nutzer selbst**, mit Ansage oder mit dem Assistenten und einem Auftrag; Rückruf aus einer Notiz. Agenten (Buddy) rufen
erst später an und nur mit Bestätigung je Anruf. Der Schalter „Anrufe annehmen“ ist schon dauerhaft (bleibt wie er ist).

Zwei Schritte wie bei Etappe 2:
- **3a** Anrufen mit Ansage: Nummer eingeben → HydraHive wählt über die FRITZ!Box → wenn abgenommen wird, liest es die
  Ansage vor und legt auf. Mit Auflegen-Knopf, Status und Eintrag in der Anrufliste.
- **3b** Anrufen mit Assistent und Auftrag (z. B. „Frag nach einem Termin nächste Woche“) und „Zurückrufen“ an einer
  Notiz. Baut auf 3a und der Gesprächsschleife aus 2b auf.

## Ausgangslage (geprüft)

- Anmeldung an der FRITZ!Box 6591 über das WLAN der .2 läuft, Anrufe annehmen (2a/2b, 0.8.3) läuft live.
- Die FRITZ!Box verlangt bei INVITE von Nebenstellen in der Regel eine Digest-Anmeldung (401/407) wie beim REGISTER –
  `sip/digest.py` kann das schon (MD5/SHA-256, qop=auth).
- Der Socket des `SipAgent` ist der einzige SIP-Socket (fester Port 5070). Ausgehende Anrufe müssen über **denselben**
  Socket laufen (die FRITZ!Box kennt uns nur unter dieser Adresse); Antworten kommen in `_serve` an und werden heute
  schon per Call-ID an `CallDispatcher.handle_response` gegeben.
- `CallSession` (eingehend) und die Gesprächsschleife (`agent/conversation.py`) sind von SIP getrennt und
  wiederverwendbar; RTP/G.711/Ansage ebenso.
- Höchstens ein Anruf gleichzeitig (heute für eingehend) gilt künftig für beide Richtungen.

## Ablauf eines ausgehenden Anrufs (RFC 3261 §13, §17.1.1, §22)

INVITE (an `sip:<nummer>@<anlage>`, From = eigener Benutzername, Contact = eigene Adresse, SDP-Angebot PCMA + PCMU,
eigener RTP-Port) → `100` → ggf. `401/407` → ACK auf die Fehlerantwort, INVITE erneut mit Anmeldung (neuer CSeq,
gleiche Call-ID) → `180/183` (klingelt) → `200 OK` mit SDP der Gegenseite → **ACK** (an den Contact aus 200,
To-Tag übernehmen) → Ansage als RTP → 0,5 s Stille → `BYE` → `200`.

Sonderfälle:
- **Auflegen-Knopf, solange es klingelt** → `CANCEL` (gleicher Branch wie der INVITE) → `200` auf CANCEL + `487` auf
  INVITE → ACK auf 487. Ergebnis „abgebrochen“.
- **Niemand nimmt ab** nach höchstens 45 s Klingeln → wie Auflegen-Knopf, Ergebnis „keine Antwort“.
- **Besetzt / abgelehnt** (486, 600, 603) → ACK, Ergebnis „besetzt“ bzw. „abgelehnt“. 404/484 → „Nummer ungültig“.
  Andere 4xx/5xx/6xx → „fehlgeschlagen (Code)“.
- **Anmeldung abgelehnt** (zweites 401/407 bzw. 403) → Ergebnis „Anlage verweigert“, **kein** weiterer Versuch.
- **Auflegen-Knopf im Gespräch / Gegenseite legt auf (BYE)** → wie bei eingehend.
- **Wiederholungen**: INVITE ohne Antwort nach T1 verdoppelnd wiederholen (bis 32 s, dann „nicht erreichbar“);
  wiederholtes 200 OK erneut mit ACK beantworten.
- **Kein gemeinsamer Codec** in der 200-Antwort → ACK, sofort BYE, Ergebnis „codec“.
- Läuft schon ein Anruf (rein oder raus) → Wählen wird abgelehnt („Leitung belegt“). Ein eingehender INVITE während
  eines ausgehenden Anrufs → `486 Busy Here` (heutige Regel).
- Gesprächs-Höchstdauer: Ansage wie heute 60 s; Assistent (3b) 5 Minuten.

## Sicherheit und Kosten (verbindlich)

1. **Wer darf wählen?** Nur der angemeldete Eigentümer der Verbindung über die Oberfläche/API (`require_principal`,
   eigene Verbindung). Kein Agenten-Werkzeug, kein Auslösen durch Anrufer oder Modelltext (SPEC-V1 §4.3, §9).
2. **Nummernregeln** (`backend/dialrules.py`, rein, getestet):
   - erlaubt sind nur Ziffern, optional `+` am Anfang; Leerzeichen, `-`, `/`, `(`, `)` werden entfernt; 3–20 Ziffern.
   - **immer gesperrt** (nicht freischaltbar): Notruf `110`, `112`, `115`, `116xxx`; FRITZ!Box-Steuercodes (`#`, `*`,
     z. B. `**…`, `#96*…`).
   - **gesperrt, solange nicht freigegeben** (Schalter je Verbindung, Standard aus): Mehrwert/Premium `0900`, `0137`,
     `0138`, `0180`, `0181` (international), `0190`, `118xx` (Auskunft), `012` (Innovative Dienste), `032`, Satellit/
     internationale Sondernetze `+88…`/`0088…`; **Ausland** (`00…` bzw. `+` ohne `+49`).
   - erlaubt: deutsche Festnetz- und Mobilnummern (`0[2-9]…`, `015/016/017`), `+49…` (wird zu `0…`).
     Interne FRITZ!Box-Rufe (`**…`) sind in Etappe 3 nicht erlaubt (später, eigener Schalter).
   - Ortsnummern ohne Vorwahl (beginnt nicht mit `0`/`+`) werden abgelehnt („Bitte mit Vorwahl eingeben“) – sonst
     hängt es von der Ortsvorwahl der FRITZ!Box ab, wohin gewählt wird.
3. **Mengengrenze**: höchstens 20 ausgehende Anrufe je Tag und Verbindung (Zähler aus der Anrufliste, Ergebnis egal,
   auch Fehlversuche zählen); höchstens 1 gleichzeitig; zwischen zwei Wählversuchen mindestens 5 s.
4. **Anrufliste**: ausgehende Anrufe mit Richtung „raus“, Ziel **maskiert** wie eingehend (`•••` + letzte 3 Ziffern);
   die volle Nummer wird nicht gespeichert. Kein Ton, kein Wortlaut.
5. **Ansagetext** beim ausgehenden Anruf: Eingabe je Anruf (max. 500 Zeichen), bei leerem Feld ein fester Text
   „Hallo, hier ist der digitale Assistent von <Name>. …“. Der Text wird nicht gespeichert, nur ob es eine Ansage war.
6. KI-Hinweis: Bei 3b sagt der Assistent zu Beginn, dass er eine KI ist (wie eingehend).
7. Rufnummernunterdrückung/Absender macht die FRITZ!Box (Einstellung der Nebenstelle); HydraHive setzt keine
   eigene Absendernummer.

## Dateien (3a)

- `migrations/004_outbound.sql` – Spalten an `module_telephony_calls`: `direction` (`in`/`out`, Standard `in`),
  `kind` (`greeting`/`assistant`); an der Verbindung: `allow_premium`, `allow_foreign` (je 0).
- `backend/dialrules.py` – Nummer prüfen und normalisieren (`check(number, allow_premium, allow_foreign)` →
  normalisierte Nummer oder `Blocked(code)`).
- `backend/sip/outbound.py` – `OutboundCall`: INVITE mit Digest, Wiederholung, 1xx/2xx/4xx–6xx, ACK, CANCEL, BYE;
  nutzt RTP/G.711/Ansage wie `CallSession`. Eigene Datei, damit `call.py` < 200 Zeilen bleibt.
- `backend/sip/dispatch.py` – „belegt“ gilt für beide Richtungen; Antworten per Call-ID an den ausgehenden Anruf.
- `backend/sip/agent.py` – `dial(number, audio_fn)` startet einen `OutboundCall` über den eigenen Socket (nur wenn
  angemeldet); `hangup()`.
- `backend/outbound.py` + Routen `POST /connection/dial`, `POST /connection/dial/hangup`, `GET /connection/dial` (Status
  des laufenden Anrufs: klingelt / verbunden / beendet + Ergebnis).
- Frontend: Reiter **„Telefonaufträge“** (heute Platzhalter) → Nummer, Ansagetext, „Anrufen“, Status, „Auflegen“;
  Freigabe-Schalter Premium/Ausland in den Einstellungen; Anrufliste mit Pfeil rein/raus. Texte DE/EN.
- Tests: **Test-Anlage** (`tests/_fake_pbx.py`): nimmt INVITE an, verlangt Digest, klingelt, nimmt ab (200 + SDP),
  zählt RTP, schickt BYE / 486 / 404 / lässt klingeln; prüft ACK, CANCEL, BYE.

## Reihenfolge (TDD: rot → grün → Mutantenprobe)

1. Nummernregeln (inkl. Notruf, Steuercodes, Premium, Ausland, Normalisierung)
2. `OutboundCall` gegen Test-Anlage: normal, Digest 401 und 407, falsches Kennwort, besetzt, abgelehnt, ungültig,
   keine Antwort (CANCEL), Auflegen beim Klingeln, Auflegen im Gespräch, Gegenseite legt auf, wiederholtes 200,
   fremde RTP-Quelle, kein Codec
3. Agent/Dispatcher: belegt in beide Richtungen, Antworten richtig zugeordnet, Wählen nur wenn angemeldet
4. Speicher + API: nur eigene Verbindung, Grenzen (Tag, Abstand), Anrufliste mit Richtung, Nummer nur maskiert
5. Oberfläche + Texte
6. Live: .2 ruft Tills Testnummer an (die Nummer steht nur im Live-Test, nie im Repo), Till bestätigt „Ansage gehört“,
   Auflegen-Knopf beim Klingeln, „besetzt“ falls möglich

## Akzeptanzkriterien 3a

- Till drückt „Anrufen“, sein Telefon klingelt, er hört die Ansage, HydraHive legt auf; Eintrag „raus“ in der Liste.
- Auflegen-Knopf beim Klingeln beendet das Klingeln.
- Notrufnummern und Steuercodes werden nie gewählt; Premium/Ausland nur mit Freigabe.
- Eingehende Anrufe funktionieren unverändert (Gegenprobe).
- Volle Modul-Suite, ruff, tsc/eslint/vitest grün; Mutantenprobe.

## 3b (nach 3a, eigener PR)

- „Anrufen mit Assistent“: Felder **Auftrag** (was soll erreicht werden, max. 1000 Zeichen) und **Darf nennen**
  (welche Infos der Assistent weitergeben darf). Gesprächsschleife aus 2b mit eigenem Systemtext für ausgehende Anrufe:
  stellt sich als KI-Assistent von <Name> vor, nennt den Grund, holt nur Informationen ein, **keine Zusagen/Buchungen/
  Zahlungen** (SPEC-V1 §4.3), beendet höflich, Notiz mit Ergebnis.
- „Zurückrufen“ an einer Notiz mit Rückrufnummer: füllt Nummer und Auftrag („Rückruf zu: <Anliegen>“) vor; der Nutzer
  bestätigt mit „Anrufen“. Die Nummer aus der Notiz ist eine Anrufer-Angabe → wird wie jede Eingabe geprüft und vor dem
  Wählen angezeigt.
- Die Rückrufnummer in Notizen ist schon heute gespeichert (vom Anrufer genannt); maskiert wird nur die Absender-Nummer
  der Anlage.

## Nicht in Etappe 3

- Agenten/Buddy rufen an (später, nur mit Bestätigung je Anruf)
- geplante Anrufe / Zeitfenster / Wiederholungen (SPEC-V1 §8)
- interne Rufe an FRITZ!Box-Nebenstellen
- Kontaktmanager (eigener Task), Archiv mit Ton/Volltranskript
