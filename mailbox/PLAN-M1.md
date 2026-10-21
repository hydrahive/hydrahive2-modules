# Plan Mailbox M1 – Konten, Abgleich, Archiv, Webmail lesen

Spec: `mailbox/SPEC.md` (freigegeben von Till am 21.10.2026). Modul-Version 0.1.0.

## Ziel

Nach M1 kann Till persönliche Mailkonten (IMAP mit Passwort, Gmail mit App-Passwort) anlegen. Alle Ordner und alle Jahre
werden vollständig als `.eml`-Archiv abgelegt (es wird nie gelöscht) und durchsuchbar gemacht. Im Webmail kann er lesen:
drei Spalten, Suche, Unterhaltungen, sichere HTML-Anzeige, Anhänge herunterladen. Schreiben, gemeinsame Konten,
Projektfreigaben, Agenten-Werkzeuge und Samba folgen ab M2.

## Vorab geprüft (21.10.2026)

- `imaplib.IMAP4.idle()` gibt es erst ab **Python 3.14**. Der Kern verlangt `>=3.12`, der Mac-Testrechner hat 3.12.
  → In M1 wird **im Takt abgefragt** (Standard alle 5 min, „Jetzt abrufen“ per Knopf). IDLE folgt in M2 mit einer kleinen
  eigenen Umsetzung (`IDLE`/`DONE` über `_command`), damit es auch unter 3.12 läuft.
- Python unter Linux hat SQLite FTS5 (3.46.1, geprüft). Auf dem Mac (brew-Python) wird das beim Start geprüft. Fehlt
  FTS5, sucht das Modul mit `LIKE` und zeigt einen Hinweis (Test mit erzwungenem Fallback).
- Modulmuster wie bei `legal`: `register(ctx)`, Migrationen `migrations/*.sql`, `ctx.register_job`, Tests mit
  `_hh_isolation.py` + `only_own_rows`, Frontend `index.tsx` mit Routen und Navigation.
- Testserver für echtes IMAP: **Dovecot auf hydratest** (Paket `dovecot-imapd` 2.3.21 verfügbar). Nur für die
  Abnahme vor Till, mit Wegwerf-Postfächern, danach wieder entfernt.

## Entscheidung: zwei Datenbanken

- **Kern-Datenbank** (`sessions.db`, Migrationen des Moduls): nur das Kleine und Unersetzliche, also Konten (mit
  verschlüsseltem Geheimnis), Abgleich-Status, später Freigaben und Protokoll. Es ist im System-Backup enthalten.
- **Eigener Index** `<archiv>/index.sqlite` (WAL): Ordner mit UID-Stand, Nachrichten, FTS5. Er kann groß werden
  (alle Jahre) und gehört deshalb **nicht** in `sessions.db`, die bei jedem System-Backup ganz kopiert wird. Der Index
  lässt sich jederzeit aus den `.eml` neu aufbauen (`rebuild`). Fehlt er, holt der nächste Abgleich nur Fehlendes
  (Abgleich über Message-ID + Hash).
- Das Archiv (`.eml` + Index) liegt **nicht** im System-Backup des Kerns. Es ist selbst das Backup (Spec §5a) und
  wird über Samba gesichert bzw. erreicht (M2b).

## Dateien (jede ≤ 200 Zeilen)

| Datei | Aufgabe |
|---|---|
| `mailbox/manifest.json` | id `mailbox`, Name „Mailbox“, Capability `module.mailbox`, `sensitive_tools` folgt ab M3 |
| `mailbox/migrations/001_mailbox.sql` | Kern-DB: `module_mailbox_accounts`, `module_mailbox_sync` |
| `backend/index_db.py` | eigener Index `index.sqlite`: Schema (Ordner, Nachrichten, FTS5 bzw. Ersatz), Verbindung, `rebuild` |
| `backend/__init__.py` | `register(ctx)`: Router, Job `sync`, Migrationen |
| `backend/secrets.py` | Passwort verschlüsseln/entschlüsseln (AES-GCM aus `hydrahive.credentials._crypto`, eigener Kontext `mailbox`) |
| `backend/providers.py` | bekannte Anbieter (Gmail, GMX, Web.de, IONOS, Strato, Posteo, Outlook) → Host/Port/TLS, Hinweis App-Passwort |
| `backend/netcheck.py` | Host prüfen: kein localhost/LAN/Link-local ohne Admin-Freigabe (SSRF), nur Ports 993/143/465/587/25 |
| `backend/accounts.py` | Konto anlegen/ändern/entfernen (nur eigene), Verbindung testen, Status |
| `backend/imap_conn.py` | Verbindung (TLS Pflicht, Zertifikat prüfen), Login, LIST mit SPECIAL-USE, UTF-7-Ordnernamen |
| `backend/fetch.py` | Je Ordner: UIDVALIDITY, neue UIDs in Paketen (200), `BODY.PEEK[]`, Flags-Abgleich, Server-Löschungen erkennen |
| `backend/parse.py` | Rohmail → Kopfdaten, Text (Klartext oder aus HTML), Anhangsliste, Thread-Schlüssel |
| `backend/archive.py` | `.eml` schreiben (Pfad §5a, Name nur vom Server), umziehen statt löschen, `MANIFEST.tsv` anhängen |
| `backend/store.py` | DB-Zugriffe: Upsert Nachricht, Flags, `deleted_on_server`, Ordnerzähler |
| `backend/search.py` | FTS5-Abfrage mit Filtern (`von:` `an:` `betreff:` `hat:anhang` `vor:` `nach:` `konto:` `ordner:`), LIKE-Fallback |
| `backend/threads.py` | Unterhaltungen: References/In-Reply-To, sonst normalisierter Betreff |
| `backend/sanitize.py` | HTML bereinigen: erlaubte Tags/Attribute, `cid:` → Anhang-URL, externe Bilder → Platzhalter bis zur Freigabe |
| `backend/sync_job.py` | Job: Konten nacheinander, Sperre je Konto, Fortschritt in `_sync`, Fehler als Kontostatus |
| `backend/routes.py` | `/accounts` (CRUD, test, sync), `/folders`, `/messages` (Liste, Suche), `/messages/{id}` (Kopf, Text, Anhänge) |
| `backend/body_routes.py` | `/messages/{id}/html` (bereinigt, mit CSP, für das iframe), `/attachments/{id}/{n}`, `/messages/{id}/eml` |
| `frontend/index.tsx` | Route `/mailbox/*`, Navigation, i18n de/en |
| `frontend/api.ts` | API-Aufrufe und Typen |
| `frontend/MailboxPage.tsx` | drei Spalten, schmal: jeweils eine |
| `frontend/FolderTree.tsx` · `MessageList.tsx` · `MessageView.tsx` | Spalten |
| `frontend/AccountDialog.tsx` | Konto-Assistent (Adresse → Vorschlag, Test, Speichern) |
| `frontend/SearchBar.tsx` | Suchfeld mit Filter-Hilfe |
| `frontend/mailFormat.ts` (+ `.test.ts`) | Datum, Größe, Absender kurz, Filter-Parser für die Anzeige |
| `frontend/useKeys.ts` | Tastenkürzel j/k, Enter, / , e(rchiv folgt M2) |
| `tests/…` | je Backend-Datei eine Testdatei, Fixtures `tests/fixtures/*.eml`, Fake-IMAP |

## Testaufbau

- **Fake-IMAP** (`tests/_fake_imap.py`): Er bildet die genutzten `imaplib`-Befehle (`login`, `list`, `select`, `uid
  search/fetch`, `status`) auf In-Memory-Ordner ab, mit UIDVALIDITY und Flags. Er wird über eine Fabrik eingehängt
  (`imap_conn.open = …`), nicht per Monkeypatch tief im Code.
- **Echte Mails** als Fixtures: Klartext, HTML mit externen Bildern und `<script>`, multipart/alternative, Anhänge
  (PDF, Bild inline per `cid:`), Umlaute im Betreff (RFC 2047), ISO-8859-1-Körper, fehlende Message-ID, kaputte
  Datumsangabe, sehr große Mail (Grenze).
- **Echter Server** erst in der Abnahme: Dovecot auf hydratest (Schritt 13).

## Reihenfolge (TDD: Test rot → grün → Mutanten-Gegenprobe ohne Bytecode-Cache)

1. **Gerüst**: manifest, Migration, `register`, `index_db`. Test: Migration läuft (Kern-Tabellen), Index-Schema mit
   FTS5 entsteht im Archivordner, `register` meldet Router/Job/Migrationen. Fallback-Test ohne FTS5.
2. **secrets**: Passwort rundum verschlüsselt, nie im Klartext in der DB. Falscher Schlüssel → Fehler, kein Klartext.
3. **providers + netcheck**: Gmail-Vorschlag mit Hinweis App-Passwort. `127.0.0.1`, `192.168.x`, `::1`, `169.254.x`,
   Namen, die auf interne Adressen zeigen → abgelehnt (DNS-Auflösung testbar über injizierte Funktion). Port 8080 → abgelehnt.
4. **parse**: alle Fixtures → richtige Kopfdaten, Text, Anhänge. Nie Ausnahme bei kaputter Mail (Fehlerfeld statt Absturz).
5. **archive**: Pfad nach §5a, Dateiname nur aus Datum/bereinigtem Betreff/Hash (Test mit `../`, `/`, `\0`, Emoji,
   300 Zeichen), gleiche Mail zweimal → eine Datei, Umzug bei Ordnerwechsel, **niemals unlink** (Test prüft, dass es im
   Modul kein `unlink`/`rmtree` auf Archivpfade gibt), `MANIFEST.tsv` mit SHA-256.
6. **store + threads**: Upsert, Flags, Unterhaltungen aus References, Betreff-Fallback („AW:“/„Re:“/„WG:“/„Fwd:“).
7. **fetch** (gegen Fake-IMAP): Erstabgleich alle Ordner in Paketen. Zweiter Lauf holt nur Neues. UIDVALIDITY-Wechsel →
   Ordner neu einlesen ohne Doppelte (Abgleich über Message-ID + Hash). Mail auf Server gelöscht → `deleted_on_server`,
   Datei bleibt. Flags-Änderung kommt an. Abbruch mitten im Paket → nächster Lauf macht weiter.
8. **search**: FTS-Treffer, alle Filter, Sortierung, LIKE-Fallback liefert dieselben Treffer für die Testfälle.
   Eingaben mit FTS-Sonderzeichen (`"`, `*`, `NEAR`) brechen nicht und werden nicht als Operator verstanden.
9. **sanitize**: `<script>`, `on*`-Attribute, `javascript:`-Links, `<iframe>`, `<form>`, `style` mit `url()`, `<base>`,
   `<meta refresh>` entfernt. Externe `<img>` → Platzhalter. `cid:` → Anhang-URL. Ausgabe mit CSP
   `default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'`.
10. **sync_job + accounts**: Konto anlegen prüft Verbindung. Falsches Passwort → klare Meldung, Status „Anmeldung
    fehlgeschlagen“. Job holt alle Konten, Fehler in einem Konto stoppt die anderen nicht. Sperre verhindert doppelten Lauf.
11. **Routen** über den echten Kern: ohne Login 401, ohne `module.mailbox` 403, **fremdes Konto/fremde Mail → 404**
    (auch per erratener ID), Anhang-Index außerhalb → 404, Passwort nie in einer Antwort.
12. **Frontend**: vitest für `mailFormat` und Komponenten (`renderToStaticMarkup`): Liste, Ansicht mit
    `iframe sandbox` (ohne `allow-scripts`), „Bilder laden“-Knopf, leere Zustände, kein `dangerouslySetInnerHTML`.
    tsc + eslint.
13. **Abnahme vorher** auf hydratest: Dovecot mit zwei Wegwerf-Postfächern und etwa 2.000 eingespielten Mails
    (Fixtures + erzeugte). Abgleich, Suche, Löschung auf dem Server, UIDVALIDITY-Wechsel und Neustart mitten im
    Abgleich, alles gegen den echten Server. Danach Dovecot + Postfächer entfernen.
14. hh-review, security-audit, Version, PR, CI. Merge nach Tills OK, Update durch Till.
15. **Abnahme durch Till**: eigenes Konto anlegen, Archiv vollständig (Anzahl je Ordner = Server), alte Mail finden,
    HTML-Mail ohne externe Bilder, Anhang öffnen. Auf dem Mac-Testrechner: Modul läuft, Abgleich mit einem Konto.

## Akzeptanzkriterien M1

- Konto anlegen mit IMAP-Passwort oder Gmail-App-Passwort. Das Passwort steht nirgends im Klartext (DB, Logs, Antworten).
- Erstabgleich holt **alle Ordner, alle Jahre**. Die Anzahl je Ordner stimmt mit dem Server überein.
- Jede Mail liegt als `.eml` nach §5a. Server-Löschung → Mail bleibt lokal (`deleted_on_server`). Im Modul gibt es keinen
  Löschpfad für Archivdateien.
- Suche über alle Konten mit Filtern, Antwort unter 1 s bei 50.000 Mails (Messung im Schritt 13 mit erzeugten Mails).
- HTML-Mails ohne Skripte, externe Bilder erst nach Klick.
- Fremde Konten und Mails sind unsichtbar (404).
- Läuft unter Python 3.12 und 3.14, Linux und macOS.

## Nicht in M1

Schreiben/Senden/Entwürfe/Verschieben/Löschen (M2), IDLE (M2), Backup-Prüfung + Samba (M2b), gemeinsame Konten,
Projektfreigaben, Agenten-Werkzeuge (M3), Senden durch Agenten (M4), Microsoft-/Google-OAuth (M1b, zum Schluss).
