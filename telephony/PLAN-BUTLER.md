# Plan: VoIP am Butler – Anruf kommt rein → Ablauf entscheidet

Auftrag Till, 25.10.2026: „Ich will, dass wenn ein Anruf eingeht, ich das im Butler behandeln kann: wenn Anruf eingeht
von … und Mo–Fr, dann mache dies. Ich will nicht, dass der Butler erst nach einem Anruf greift – das ist zwar auch gut,
aber primär sinnlos, wenn ich einen Anruf nicht als Auslöser habe.“

→ **Hauptsache: Auslöser „Anruf kommt rein“** – feuert, während es klingelt, **bevor** HydraHive abnimmt. Der Ablauf
entscheidet, was mit **diesem** Anruf passiert. „Anruf beendet“ kommt danach als Zusatz.

## Entscheidungen Till (25.10.)
- Reihenfolge B1 → B2 → B3 passt.
- Schalter „Anrufe annehmen“ aus + Ablauf sagt „annehmen“ → **Ablauf gewinnt**.
- Neu (Idee Till): **PIN per Tastatur** – Anrufer gibt eine PIN ein, ist dann authentifiziert und bekommt andere
  Grenzen/Rechte. → eigener Abschnitt „PIN“ unten (eigene Etappe, Fragen offen).

## Ausgangslage (geprüft im Code)

- Module steuern Butler-Bausteine ohne Kern-Änderung bei (`ctx.register_butler_trigger/condition/action`,
  `modules/butler_bridge.py`); Vorbild `cryptoboard/backend/alerts.py`.
- `executor.dispatch_event(event, owner=<Benutzername>)` läuft durch die eingeschalteten Abläufe dieses Nutzers und
  liefert je Treffer `actions_executed` mit den Rückgaben der Aktionen (`ActionResult`: ok, detail, reply_text,
  reply_via_agent, reply_prefix, stop_default). Kanäle (`butler/dispatch.py`) werten das danach aus –
  **Aktionen geben also Anweisungen zurück, und der Aufrufer setzt sie um.** Genau so machen wir es beim Anruf.
- Vorhandene Kern-Bedingungen: **Wochentag** (`day_of_week`), **Uhrzeit** (`time_window`), **Kontakt in Liste**
  (`contact_in_list`, vergleicht `event.contact_id`), **Feld gleich/enthält** (`payload_field_*`), Text/Regex.
  Wochentag/Uhrzeit nutzen die Serverzeit – die .2 steht auf Europe/Berlin. ✔
- Kern-Aktion „Agent antworten lassen“ (`agent_reply`) setzt nur einen Hinweis; ausgeführt wird er heute nur von
  Kanälen und vom Zeitplan (`butler/_scheduled_agent_run.run_scheduled_agent_actions`).
- Ereignisdaten werden **nicht** gespeichert (nur Rückgabe an den Aufrufer) – volle Rufnummer im Ereignis ist ok.
- ⚠ **Butler-Editor kennt nur fest eingebaute Bausteine**: `frontend/src/features/butler/palette-data.ts`
  (PALETTE_STRUCTURE) und `properties/registry.tsx` (FORMS) sind statische Listen. Modul-Bausteine (auch
  cryptoboard `crypto_price`) erscheinen **nicht** in der Palette und haben kein Formular. Das Backend nimmt sie beim
  Speichern an (Registry), aber anlegen kann man sie in der Oberfläche nicht. → **Ohne Kern-Änderung ist der
  Butler-Teil für Till nicht bedienbar.** Lösung: Kern-PR „Modul-Bausteine im Butler-Editor“ – Backend liefert die
  Registry (Label, Beschreibung, ParamSchema) über eine Route, die Palette zeigt eine Gruppe „Module“, und für
  Bausteine ohne eigenes Formular baut der Editor das Formular aus dem ParamSchema (text, textarea, select, number,
  checkbox, list_text). Nutzt auch cryptoboard. Klein und allgemein; braucht Tills OK (Kern).

## Ablauf eines eingehenden Anrufs mit Butler

INVITE → `100 Trying` → `180 Ringing` → **Butler fragen** (im Hintergrund, höchstens 3 s, das Telefon klingelt weiter)
→ Ergebnis des ersten passenden Ablaufs bestimmt, was passiert → sonst wie heute (Schalter/Einstellungen).

Ereignis `telephony_call_incoming`:
- `owner` = Benutzername des Verbindungs-Inhabers (aus `user:<id>` → Benutzer).
- `contact_id` = **Rufnummer des Anrufers** (Ziffern, `+49…` → `0…`) – damit funktioniert die vorhandene Bedingung
  „Kontakt in Liste“ direkt mit Nummern. Ohne Nummer (unterdrückt): leer.
- `payload`: `number` (wie contact_id), `number_masked`, `anonymous` (true/false), `connection_id`.
- `channel` = "telephone".

## Neue Bausteine

### Auslöser
1. **„Anruf kommt rein“** (`telephony_call_incoming`). Einstellung: optional „nur diese Nummern“ (Liste) – damit
   reicht für den häufigsten Fall **ein** Baustein; „Mo–Fr“ und Uhrzeit mit den vorhandenen Bedingungen.
2. **„Anruf beendet“** (`telephony_call_ended`) – Zusatz: nach jedem Anruf mit Notiz/Ergebnis (wie im ersten Entwurf;
   Rückrufnummer nicht im Ereignis, Nummer maskiert).

### Bedingungen
1. **„Anrufer-Nummer“** (`telephony_caller`): Nummer beginnt mit / ist eine von / ist unterdrückt. Für „von …“ geht auch
   die vorhandene „Kontakt in Liste“; diese hier kann zusätzlich Vorwahlen („beginnt mit 030“) und „unterdrückt“.
2. **„Notiz-Merkmal“** und **„Anruf-Ergebnis“** – nur für „Anruf beendet“ (wie im ersten Entwurf).

### Aktionen für „Anruf kommt rein“ (bestimmen, was mit dem Anruf passiert)
1. **„Mit Assistent annehmen“** – optional **eigener Wissenstext** und **eigener Name** für diesen Ablauf (z. B. für
   Kunden-Nummern anderes Wissen als für Unbekannte). Leer = Einstellungen.
2. **„Mit Ansage annehmen“** – optional eigener Ansagetext.
3. **„Ablehnen“** – andere Telefone klingeln weiter (wie Schalter aus, 480).
4. **„Besetzt“** – 486 (Anrufer hört besetzt).
5. **„Normal behandeln“** – nichts entscheiden (Einstellungen gelten). Nützlich im „Nein“-Zweig.
- Die erste entscheidende Aktion gewinnt (wie bei Kanälen „erste stop-Aktion gewinnt“).
- **Kombinierbar** mit Kern-Aktionen im selben Ablauf, z. B. „Agent antworten lassen“ → HydraHive schickt dir parallel
  eine Nachricht/startet einen Agenten („Anruf von Max Mustermann läuft“). Dafür rufen wir nach dem Ablauf
  `run_scheduled_agent_actions` auf (wie der Zeitplan) – **im Hintergrund**, der Anruf wartet nicht darauf.

### Aktionen „selbst anrufen“ (aus dem ersten Entwurf, unverändert)
- **„Anrufen“** (Ansage oder Assistent mit Auftrag; Nummer fester Text) und **„Zurückrufen“** (Nummer aus der eigenen
  Notiz). Nutzbar z. B. mit Zeitplan-Auslöser oder nach „Anruf beendet“.

## Beispiele
- *Anruf kommt rein von 0301234567, 0151… (Familie) → Mo–Fr 9–17 Uhr → „Mit Assistent annehmen“ (Wissen: „Ich bin in
  der Arbeit, rufe abends zurück“); sonst → „Ablehnen“* (Telefone klingeln normal).
- *Anruf kommt rein → Nummer unterdrückt → „Besetzt“.*
- *Anruf kommt rein → Sa/So → „Mit Ansage annehmen“ („Am Wochenende nicht erreichbar …“) + „Agent antworten lassen“
  (schickt dir eine Nachricht, wer angerufen hat).*
- *Anruf beendet → Notiz „Rückruf gewünscht“ → Agent fasst zusammen / Assistent ruft zurück.*

## Regeln und Sicherheit
1. **Kein passender Ablauf / Butler-Fehler / Zeit abgelaufen (3 s)** → Verhalten wie heute (Einstellungen). Ein
   kaputter Ablauf kann Anrufe nie blockieren.
2. **Schalter „Anrufe annehmen“ aus + Ablauf sagt „annehmen“** → Ablauf gewinnt (sonst wäre der Butler nutzlos).
   Wird so im Schalter-Text erklärt: „Butler-Abläufe gehen vor.“ → *Frage an Till.*
3. Die Anrufer-Nummer ist **nicht geprüft** (kann gefälscht sein) – nur zum Sortieren, nie zum Freischalten von Wissen
   oder Rechten. Der Assistent bleibt bei „Anrufer = Fremder“, auch für Nummern auf einer Liste. Steht im Bausteintext.
4. Rufnummern (voll) stehen nur im Ereignis (nicht gespeichert). In der Anrufliste bleibt sie maskiert. Agent-Aktionen
   bekommen das Ereignis (inkl. Nummer) – das ist gewollt („wer hat angerufen“) und bleibt beim Nutzer.
5. Selbst anrufen über den Butler: nur über die Verbindung des **Ablaufbesitzers** (`event.owner`; leer → kein Anruf),
   Nummer nie aus Vorlagen, gleiche Grenzen wie der Knopf, Schleifenschutz (`via_butler`). Kern-PR „Executor setzt
   `event.owner = flow.owner`“ bleibt empfohlen (eine Zeile + Test, Tills OK).
6. Probelauf im Butler-Editor ruft/antwortet nie (Executor führt Aktionen im Probelauf nicht aus).

## Dateien
- `backend/butler_events.py` – Ereignisse bauen und senden (eingehend synchron mit Zeitgrenze, beendet im Hintergrund).
- `backend/butler_specs.py` – Auslöser, Bedingungen, Aktionen (Specs).
- `backend/calls.py` – `decide(cid, from_number)`: Butler fragen → Entscheidung (annehmen mit Assistent/Ansage +
  Überschreibungen, ablehnen, besetzt, normal).
- `backend/sip/dispatch.py` – nach `180 Ringing` die Entscheidung holen (im Anruf-Thread, nicht im SIP-Empfang).
- `backend/__init__.py` – registrieren.
- Tests: Specs; echter Butler-Executor mit Test-Abläufen (Nummer in Liste, Wochentag, Ja/Nein-Zweig); Zeitgrenze;
  kaputter Ablauf; Schalter aus + Ablauf; Test-Anrufer über SIP (Ablehnen → 480, Besetzt → 486, Assistent mit
  eigenem Wissen); keine volle Nummer in der Anrufliste.

## Reihenfolge
1. **Etappe B1 – „Anruf kommt rein“**: Auslöser, Bedingung „Anrufer-Nummer“, Aktionen annehmen/ablehnen/besetzt/normal,
   Einbau in den Anrufablauf. Live: Ablauf „von <Testnummer> Mo–Fr → Assistent mit eigenem Wissen, sonst ablehnen“.
2. **Etappe B2** – „Agent antworten lassen“ beim eingehenden Anruf (Nachricht an dich).
3. **Etappe B3** – „Anruf beendet“ + Notiz-Bedingungen + „Anrufen“/„Zurückrufen“.

## PIN per Tastatur (Idee Till, eigene Etappe B4 – nach B1)

Ziel: Ein Anrufer tippt eine PIN; stimmt sie, gilt er als **authentifiziert** (z. B. Till selbst von unterwegs) und
bekommt **andere Grenzen** – bis hin zu einem eigenen Assistenten-Profil.

Technik (geprüft): Die FRITZ!Box bietet Tastentöne als `telephone-event` (RFC 4733, Payload 101) an; HydraHive nimmt
das heute **nicht** an (Antwort-SDP nur G.711). Nötig: 101 im Antwort-SDP anbieten, RTP-Pakete mit diesem Typ als
Tasten lesen (Ende-Bit, doppelte Pakete), dazu Rückfall „Ton-Erkennung“ (Goertzel/DTMF im Ton) falls die Anlage die
Töne im Sprachkanal schickt. Eingabe: Ziffern + `#` zum Abschließen, Zeitgrenze 10 s.

Sicherheit (verbindlich):
- PIN nur **gehasht** gespeichert (wie Passwörter), mind. 6 Ziffern, nie im Klartext in Notiz/Ereignis/Log.
- **3 Versuche** je Anruf, danach Anruf normal weiter (oder auflegen); **Sperre** nach 10 Fehlversuchen/Tag je
  Verbindung (Schutz gegen Durchprobieren).
- Rufnummer bleibt ungeprüft – die PIN ist der eigentliche Nachweis. PIN + bekannte Nummer zusammen sind stärker
  (Option „nur von diesen Nummern“).
- Was „andere Grenzen“ heißt, ist **Tills Entscheidung** (siehe Fragen). Der Assistent bekommt auch mit PIN **keine
  Werkzeuge**, solange es keine eigene Spec dafür gibt (SPEC-V1 §9: „spätere Tools nur mit eigener Spec und
  Bestätigungsgates“).
- Im Butler: Aktion „PIN abfragen“ mit Ja/Nein-Zweig (wahr = PIN richtig), oder Ereignisfeld `pin_ok` nach einer
  Abfrage. Danach z. B. „Mit Assistent annehmen“ mit Profil „privat“.

## Fragen an Till
1. Passt die Reihenfolge (B1 zuerst)?
2. Schalter „Anrufe annehmen“ aus, aber ein Ablauf sagt „annehmen“ → **Ablauf gewinnt**?
3. Darf der Butler beim Selbst-Anrufen (B3) ohne Rückfrage anrufen, wenn du den Ablauf angelegt hast? Und der kleine
   Kern-PR (Ablaufbesitzer an Aktionen)?
4. **Kern-PR „Modul-Bausteine im Butler-Editor“** – ohne ihn sind die neuen Bausteine nicht anlegbar. OK?
5. **PIN:** Was soll nach richtiger PIN anders sein? Vorschläge: (a) längere Gesprächsdauer, (b) eigener Wissenstext
   mit privaten Infos (z. B. Termine, die nur du hören darfst), (c) eine Nachricht an dich wird sofort geschickt,
   (d) später: Assistent darf bestimmte Dinge tun (z. B. Aufgabe anlegen) – das wäre ein großer Schritt (Werkzeuge
   am Telefon) und bräuchte eine eigene Spec.
