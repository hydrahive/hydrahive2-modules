# Plan: VoIP am Butler (Auslöser, Bedingungen, Aktionen)

Auftrag Till, 25.10.2026: „wir dürfen nicht vergessen das ganze auch an den Butler anzubinden“ und „Butler-Planung
gleich dran hängen“. Stand vorher: telephony 0.10.1 – Anrufe annehmen (Ansage/Assistent) und selbst anrufen
(Ansage/Assistent mit Auftrag) laufen live an der FRITZ!Box.

## Ausgangslage (geprüft im Code)

- Module können eigene Butler-Bausteine beisteuern, **ohne Kern-Änderung**: `ctx.register_butler_trigger`,
  `register_butler_condition`, `register_butler_action` (`hydrahive/modules/context.py`), eingespeist von
  `hydrahive/modules/butler_bridge.py` nach den eingebauten Bausteinen. Kollidiert ein Name, wird der Modul-Baustein
  übersprungen. Vorbild: `cryptoboard/backend/alerts.py` (Trigger `crypto_price` + Bedingung, Poller ruft
  `hydrahive.butler.executor.dispatch_event`).
- Ein Ereignis ist `TriggerEvent(event_type, payload, owner, …)`. `dispatch_event(event, owner=…)` geht durch alle
  eingeschalteten Abläufe **dieses Nutzers** (Benutzername).
- Eine Aktion bekommt `execute(params, event)` – **nicht** den Ablauf selbst. Wem der Ablauf gehört, steht nur in
  `event.owner`, und das ist nicht bei jedem Auslöser gesetzt (z. B. bei cryptoboard `owner=None`).
  Zeitgesteuerte Abläufe setzen `owner=flow.owner` (`butler/scheduler.py`). Folge siehe Sicherheit Punkt 2.
- Texte in Aktionen können Jinja-Vorlagen sein (`butler/template.py`, Variable `event`).
- Der Butler hat schon Bedingungen für **Uhrzeit** (`time_window`), **Wochentag** (`day_of_week`) und **beliebige
  Ereignisfelder** (`payload_field_equals/contains`) – die nutzen wir mit, statt eigene zu bauen. Eine Aktion
  „warten/verzögern“ gibt es **nicht** („nicht erreicht → in 1 Stunde nochmal“ geht also erst später).
- Wer `dispatch_event` aufruft (geprüft): Kanal-Nachrichten und Zeitpläne mit `owner=<Benutzer>`;
  **cryptoboard mit `owner=None`** → dann laufen die Abläufe **aller** Nutzer, und `event.owner` ist leer.
- Benutzername → user_id: `hydrahive.access.check.user_id_for(username)`. Die VoIP-Verbindung gehört `user:<user_id>`.

## Was gebaut wird

### Auslöser (Trigger)
1. **`telephony_call_ended` – „Anruf beendet“**: feuert nach jedem Anruf (rein oder raus), auch abgelehnt/besetzt.
   Filter im Baustein: Richtung (alle/eingehend/ausgehend), Art (alle/Ansage/Assistent), „nur mit Notiz“.
   Daten im Ereignis (`payload`): `direction`, `kind`, `result`, `number` (**maskiert** `•••567`), `turns`,
   `has_note`, Notizfelder `name`, `concern`, `result_text` (Ergebnis), `summary`, `callback_wanted`,
   `needs_review`, `open_questions`, `call_id`. **Die Rückrufnummer kommt nicht ins Ereignis** (siehe Sicherheit 4);
   zurückrufen geht über die Aktion „Zurückrufen“ mit `call_id`.
2. (kein eigener „Notiz“-Auslöser – „Anruf beendet“ + Bedingung „hat Notiz“ deckt das ab, weniger Bausteine.)

### Bedingungen (Condition)
1. **`telephony_note` – „Notiz-Merkmal“**: wahr, wenn das gewählte Merkmal stimmt: „Rückruf gewünscht“,
   „Bitte ansehen“, „hat offene Fragen“, „Anrufer hat Namen genannt“.
2. **`telephony_result` – „Anruf-Ergebnis“**: Auswahl „erreicht“ / „nicht erreicht“ (no_answer, busy, declined,
   unreachable) / „abgelehnt (Schalter aus)“. Uhrzeit/Wochentag: vorhandene Kern-Bedingungen.

### Aktionen (Action)
1. **`telephony_call` – „Anrufen“**: Nummer (fester Text, **keine Vorlage**), Art Ansage/Assistent, Ansagetext bzw.
   Auftrag + „Darf nennen“ (Auftrag/Ansage dürfen Vorlagen sein, z. B. `Erinnerung: {{ event.payload… }}`).
   Ruft über dieselbe Funktion wie der Knopf (`outbound.dial`) – also mit Nummernregeln, Freigaben, Tagesgrenze,
   5-s-Abstand, einer Leitung.
2. **`telephony_callback` – „Zurückrufen“**: nur sinnvoll nach „Anruf beendet“. Holt die Rückrufnummer aus der Notiz
   des Anrufs `event.payload.call_id` (wie der Knopf „Zurückrufen“), Auftrag vorbelegt oder eigener Text. Ruft nur,
   wenn der Anruf zur Verbindung desselben Nutzers gehört.

Beispiele, die damit gehen:
- „Neue Notiz mit ‚bitte ansehen‘ → Agent fasst zusammen und schickt mir eine Nachricht“ (Kern-Aktion agent_reply).
- „Jeden Montag 8 Uhr: Assistent ruft Werkstatt an und fragt nach dem Reparaturstatus“ (Kern-Auslöser cron).
- „Anrufer wünscht Rückruf → Assistent ruft zurück: ‚Nachricht ist angekommen, wann passt ein Gespräch?‘“.
- „Ausgehender Anruf nicht erreicht → in 1 Stunde nochmal“ (braucht Verzögerung im Butler – prüfen, sonst später).

## Sicherheit (verbindlich, SPEC-V1 §2.6, §4.3, §9)

1. **Nur selbst angelegte Abläufe rufen an.** Die Planung im Ablauf gilt als Freigabe (SPEC-V1 §2.6). Es gibt
   **kein** Agenten-Werkzeug „anrufen“; ein Agent kann nur über einen Ablauf anrufen, den der Nutzer gebaut hat.
2. **Wessen Telefon?** Eine Aktion bekommt nur `event`, nicht den Ablauf. Sie braucht aber den **Ablaufbesitzer**
   (dessen FRITZ!Box-Zugang und dessen Freigaben gelten). Geprüft: `event.owner` ist der Ablaufbesitzer, wenn der
   Aufrufer `dispatch_event(owner=X)` nutzt (Kanäle, Zeitpläne, unser eigenes Ereignis). Bei `owner=None`
   (cryptoboard) laufen alle Abläufe aller Nutzer mit leerem `event.owner`.
   → **Regel im Modul (sofort):** anrufen nur, wenn `event.owner` gesetzt ist; sonst `ok=False, kein Eigentümer`.
   Unsere eigenen Ereignisse schicken wir immer mit `owner=<Benutzername des Verbindungs-Inhabers>`.
   → **Restrisiko:** Ein künftiges Modul ruft `dispatch_event(event_mit_owner=A, owner=None)` – dann liefen Abläufe
   von B mit `event.owner=A`, und B's Aktion würde über A's Telefon anrufen. Heute tut das kein Code (geprüft:
   cryptoboard setzt `owner` nicht). **Saubere Lösung: kleiner Kern-PR** – der Executor setzt vor den Aktionen
   `event.owner = flow.owner` (eine Zeile + Test). Braucht Tills OK.
3. **Nummer nie aus Text.** `telephony_call`: Nummer ist fester Text im Ablauf, wird **nicht** als Vorlage gerendert
   (sonst könnte ein Anrufer/eine Mail über `{{ event… }}` die Zielnummer bestimmen). `telephony_callback`: Nummer
   nur aus der gespeicherten Notiz des genannten eigenen Anrufs.
4. **Rückrufnummer nicht ins Ereignis.** Ereignisse landen in Ablauf-Protokollen und in Agenten-Kontext; dort reicht
   die maskierte Nummer.
5. **Gleiche Grenzen wie der Knopf**: Notruf nie, Sondernummern/Ausland nur mit Freigabe, 20/Tag, 5 s Abstand,
   eine Leitung. Zusätzlich: **Schleifenschutz** – ein von einer Butler-Aktion ausgelöster Anruf erzeugt beim Ende
   ein Ereignis mit `via_butler: true`; „Anrufen“/„Zurückrufen“ reagieren darauf nicht (sonst ruft „nicht erreicht →
   nochmal“ endlos; die Tagesgrenze würde das zwar stoppen, aber erst nach 20 Anrufen).
6. **Probelauf (dry_run)** des Butlers ruft nie an: Der Executor ruft `execute` im Probelauf nicht auf
   (`executor._run_action`, geprüft) – zusätzlich ein Test.
7. Auftrag/Ansage aus Vorlagen gehen an den Assistenten als Auftrag – sie stammen vom Nutzer bzw. aus Ereignisdaten.
   Notiztext eines Anrufers in einem Auftrag ist möglich (z. B. „Rückruf zu: {{ concern }}“) → der Assistent hat
   ohnehin keine Werkzeuge und macht keine Zusagen; die Zielnummer kann so nicht geändert werden (Punkt 3).

## Dateien

- `backend/butler.py` – Specs (Trigger, 2 Bedingungen, 2 Aktionen) + `emit_call_ended(cid, info, call_id)`.
- `backend/calls.py` – nach `record` (neue Zeile) Ereignis senden (im Hintergrund, Fehler blockieren nie den Anruf).
- `backend/outbound.py` – `dial(..., via_butler=False)`; Merker am laufenden Anruf, landet im Ereignis.
- `backend/__init__.py` – `ctx.register_butler_*`.
- Tests: Specs (Filter, Bedingungen), Ereignis-Inhalt (maskiert, keine Rückrufnummer), Aktionen gegen Fake-Agent
  (Nummernregeln greifen, kein Eigentümer → kein Anruf, fremder Anruf → kein Rückruf, Vorlage in der Nummer wird
  nicht gerendert, Schleifenschutz), echter Butler-Executor mit einem Test-Ablauf (dispatch → Aktion).
- Kern-PR (nur nach Tills OK): Executor gibt den Ablaufbesitzer an Aktionen weiter (Sicherheit 2a).

## Reihenfolge

1. Trigger + Ereignis aus `calls.record` (TDD, Mutanten)
2. Bedingungen
3. Aktion „Anrufen“ mit allen Grenzen und Lösung (b) für den Eigentümer
4. Aktion „Zurückrufen“
5. Live: Ablauf „Notiz mit Rückrufwunsch → Agent schickt mir Nachricht“ und „Zeitplan → Assistent ruft Testnummer an“
6. Optional Kern-PR (a)

## Fragen an Till

1. Passt die Auswahl (1 Auslöser, 2 Bedingungen, 2 Aktionen)?
2. Darf eine Butler-Aktion **ohne weitere Rückfrage** anrufen, wenn du den Ablauf selbst angelegt hast (Vorschlag:
   ja, wie in SPEC-V1 „Planung = Freigabe“)? Oder willst du vor jedem Butler-Anruf eine Bestätigung (z. B. per
   Nachricht „Jetzt anrufen? Ja/Nein“)?
3. Kleiner Kern-PR „Ablaufbesitzer an Aktionen weitergeben“ (eine Zeile im Executor + Test) – ok? Ohne ihn bleibt
   das oben beschriebene Restrisiko, das heute kein Code auslöst.
