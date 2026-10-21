# Plan Mailbox M2 – Schreiben, Antworten, Entwürfe, Verschieben/Löschen, IDLE

Spec: `mailbox/SPEC.md` §5, §6, §10 (Zeile M2), §11. Freigegeben von Till am 21.10.2026 („ok merge, dann weiter“).
Version 0.2.0.

## Ziel

Im Webmail lassen sich Mails schreiben, beantworten (auch an alle) und weiterleiten, mit Anhängen, Signatur je Konto
und Entwürfen. Gesendete Mails liegen danach im Gesendet-Ordner des Servers **und** im Archiv. Mails lassen sich
verschieben, markieren, als gelesen setzen und löschen. Gelöscht wird **nur auf dem Server**, die Archivdatei bleibt
(Spec §5, Archiv-Regel). Neue Mails im Posteingang erscheinen dank IMAP IDLE innerhalb von Sekunden.

## Vorab geprüft (21.10.2026)

- Kern-Versand `communication/mail/_transport.py`: Port 465 SSL, sonst STARTTLS. **Ohne** Zertifikatsprüfung mit
  eigenem Kontext, **ohne** IP-Bindung. → Mailbox bringt einen eigenen kleinen Transport mit derselben Härtung wie beim
  IMAP-Abgleich (geprüfte IP, Zertifikat gegen den Hostnamen). Der Kern bleibt unverändert.
- IMAP `IDLE`: in `imaplib` erst ab Python 3.14 (`IMAP4.idle`). Eigene Umsetzung über `_command("IDLE")` und `DONE`,
  getestet unter 3.12 und 3.14.
- Gesendet-Ordner: Gmail legt gesendete Mails selbst ab, andere Anbieter (Yahoo, GMX, Dovecot) nicht. → Nach dem
  Senden `APPEND` in den Ordner mit Rolle `sent`, **außer** der Anbieter macht es selbst (Gmail: `imap.gmail.com`).
- Ein Rate-Limit beim Senden gibt es schon in M2 (Spec §11: 20 je Stunde je Konto), nicht erst mit den Agenten.

## Dateien (jede ≤ 200 Zeilen)

| Datei | Aufgabe |
|---|---|
| `backend/compose.py` | Mail bauen: From (Absendername + Adresse des Kontos), To/Cc/Bcc geprüft, Betreff, Text + einfaches HTML, Anhänge, `Message-ID`, `Date`; Antwort/Weiterleitung: Zitat, `In-Reply-To`, `References`, Betreff-Präfix |
| `backend/addresses.py` | Empfänger prüfen: nur gültige Adressen, max. 100, keine Kopfzeilen-Injektion (CR/LF), Bcc nie in die Kopfzeilen |
| `backend/smtp_send.py` | Versand: geprüfte IP, TLS Pflicht (465 SSL / 587 STARTTLS), Zertifikat geprüft, Passwort geschwärzt in Fehlern |
| `backend/drafts.py` | Entwürfe: lokal (Kern-DB `module_mailbox_drafts`) + `APPEND` in den Entwürfe-Ordner des Servers, alten Server-Entwurf ersetzen |
| `backend/actions.py` | Verschieben (`UID MOVE`, sonst `COPY` + `\Deleted` + `EXPUNGE`), Flags setzen, Löschen (Papierkorb, sonst `\Deleted`), alles nur auf dem Server – Archiv/Index folgen über den Abgleich |
| `backend/ratelimit.py` | Versandgrenze je Konto (Standard 20/h), in der Kern-DB gezählt |
| `backend/idle.py` | IDLE auf dem Posteingang je Konto (Thread), bei neuer Mail kurzen Abgleich anstoßen; Neuverbindung nach Fehler mit Wartezeit; alle 25 min neu (RFC 2177) |
| `backend/compose_routes.py` | `POST /send`, `POST/PATCH/DELETE /drafts`, `GET /drafts`, `POST /messages/{id}/move|flags|delete` |
| `migrations/002_m2.sql` | `module_mailbox_drafts`, `module_mailbox_sendlog` (Zeitpunkt, Konto, Anzahl Empfänger – ohne Inhalt) |
| `frontend/Composer.tsx` | Schreibfenster: Absenderkonto, An/Cc/Bcc mit Vorschlägen aus dem Archiv, Betreff, Text, Anhänge, Signatur, Entwurf automatisch speichern |
| `frontend/MessageActions.tsx` | Antworten, Allen antworten, Weiterleiten, Verschieben, Löschen, Gelesen/Ungelesen, Markieren |
| `frontend/composeFormat.ts` (+ Test) | Zitat-Aufbau, Präfixe, Empfängerliste für „Allen antworten“ (ohne eigene Adresse) |

## Reihenfolge (TDD: Test rot → grün → Mutanten-Gegenprobe ohne Bytecode-Cache)

1. **addresses**: gültig/ungültig, Namen mit Umlauten (RFC 2047), CR/LF-Injektion in Name und Adresse, max. 100, Duplikate weg.
2. **compose**: neue Mail; Antwort (Re: nur einmal, In-Reply-To/References richtig, Zitat mit „Am … schrieb …“); Allen
   antworten (eigene Adresse raus, Cc bleibt); Weiterleiten (Fwd:, Anhänge des Originals optional); Signatur; Anhänge
   (Größe gesamt max. 25 MB, Dateinamen bereinigt); Bcc **nicht** in der fertigen Mail.
3. **smtp_send** (gegen Fake-SMTP): 465/587, STARTTLS Pflicht (Server ohne STARTTLS → Fehler, kein Klartext), Login,
   Empfänger aus To+Cc+Bcc, Fehlerarten (auth/tls/connect/abgelehnt), Passwort geschwärzt.
4. **ratelimit**: 20/h je Konto, danach 429 mit Restzeit, Zählung ohne Inhalt.
5. **Gesendet-Ablage**: nach dem Senden `APPEND` in `sent` mit `\Seen`; bei Gmail nicht; Fehler beim Ablegen → Mail ist
   trotzdem gesendet (Meldung, kein zweiter Versand).
6. **drafts**: anlegen, ändern (alter Server-Entwurf weg, neuer da), senden (Entwurf weg), nur eigene, Entwürfe lokal
   auch ohne Server-Entwürfe-Ordner.
7. **actions** (gegen Fake-IMAP): verschieben mit/ohne `MOVE`, löschen → Papierkorb bzw. `\Deleted`, Papierkorb leeren
   **nur auf dem Server**; Archivdatei bleibt; Flags; nur eigene Mails; nur Ordner des gleichen Kontos.
8. **Routen** über den echten Kern: Rechte, fremd = 404, Eingaben (422), Rate-Limit (429), Anhänge-Upload (multipart,
   Größe), kein Senden ohne SMTP-Server im Konto.
9. **idle** (gegen Fake-IMAP mit IDLE-Antwort): neue Mail → Abgleich angestoßen; Verbindungsabbruch → neuer Versuch
   mit Wartezeit; Stopp beim Beenden; kein IDLE, wenn der Server es nicht kann (Abfrage-Takt bleibt).
10. **Frontend**: Schreibfenster, Aktionen, Formatierung (vitest), tsc, eslint.
11. **Abnahme vorher** gegen Dovecot + Postfix (nur lokal zustellend) auf hydratest: senden → beim Empfänger da, im
    Gesendet-Ordner, im Archiv; Antwort hängt in der Unterhaltung; löschen → Server weg, Archiv bleibt; IDLE: neue Mail
    in < 10 s sichtbar. Danach alles wieder entfernen.
12. hh-review, Sicherheitsprüfung, Version 0.2.0, PR, CI. Merge nach Tills OK.
13. **Abnahme durch Till**: eine Mail an sich selbst senden, beantworten, eine löschen und im Archiv wiederfinden.

## Akzeptanzkriterien M2

- Senden mit Absendername, Anhängen, Signatur. Antwort und Weiterleitung hängen in der richtigen Unterhaltung.
- Gesendete Mail im Gesendet-Ordner des Servers und im Archiv.
- Löschen entfernt nur auf dem Server. Die Archivdatei bleibt und erscheint unter „Nur im Archiv“.
- Kein Senden ohne TLS, kein Zertifikat ohne Prüfung, keine Kopfzeilen-Injektion, Bcc bleibt verborgen.
- Höchstens 20 Mails je Stunde und Konto (einstellbar).
- Neue Mails erscheinen bei IDLE-fähigen Servern innerhalb von 10 s.

## Nicht in M2

Backup-Prüfung und Samba (M2b), gemeinsame Konten, Projektfreigaben und Agenten-Werkzeuge (M3), Senden durch Agenten
(M4), Regeln/Filter (M5), OAuth (M1b). Formatierter Editor über Fett/Kursiv/Liste hinaus.
