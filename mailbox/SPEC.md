# Mailbox – Webmail, Mailarchiv und Mail-Werkzeuge für Agenten

Status: **Entwurf** (Till 21.10.2026: „pk leg los, das ganze als modul und auf mac sollte es ja eh laufen“).
Entscheidungen Till 21.10.: Erstabgleich **alle Jahre**; **immer alles im Archiv behalten**, das Archiv ist zugleich
**Backup des Mailbestands**, erreichbar über eine **Samba-Freigabe**; Microsoft-App-Registrierung **zum Schluss**.
Modul-ID `mailbox`, Name „Mailbox“.

## 1. Ziel

1. **Webmail für den Nutzer**: Ein guter Mailclient im Browser für **mehrere Konten** (IMAP/SMTP, dazu Gmail und
   Microsoft per Anmeldung), aufgebaut wie ein gewohntes Webmail.
2. **Mailarchiv**: Alle Mails aller Konten liegen **lokal** und sind durchsuchbar, auch wenn der Server sie löscht
   (Till: „lokal speichern ist sogar gewünscht als mailarchive der ganzen mailboxen“).
3. **Agenten arbeiten mit Mails**: Projekt-Agenten (z. B. Recht) bekommen Werkzeuge zum Suchen, Lesen, Entwerfen und
   Senden, aber nur für Konten, die **das Projekt freigegeben** hat. Senden geht nur mit **Bestätigung** durch den Nutzer.
4. **Konten pro Nutzer und gemeinsame Konten** (z. B. Familie, Firma).
5. Läuft auf Linux **und macOS**, nur Python und Browser, ohne Systempakete.

## 2. Ausgangslage (geprüft 21.10.2026)

- Kern: genau **ein** globales Mailkonto (Einstellungen → Mail), Werkzeuge `send_mail` und `read_mail` (nur lesen,
  max. 50, ohne Ordner und ohne Suche), dazu der Mail-Kanal (IMAP-Polling → Agent). Das bleibt unverändert. Mailbox
  ist ein eigenes Modul daneben und ersetzt das nicht.
- Vorhanden und nutzbar: Credential-Verschlüsselung AES-GCM (`credentials/_crypto.py`), Modul-Migrationen,
  Hintergrund-Jobs (`ctx.register_job`), Modul-Werkzeuge (`ctx.register_tool`), Freigaben und Gruppen
  (`access/grants`, `groups_of`), Projekt-Mitglieder, Vault-PIN für Modul-Oberflächen (`"vault": true`),
  Datamining-Schutzstufen (`sensitive_tools`), Bestätigungsdialog für Werkzeuge (Runner, `ALWAYS_CONFIRM`).
- **Lücke im Kern**: Module können heute **keine** Bestätigung für ein eigenes Werkzeug verlangen. `ALWAYS_CONFIRM` ist eine
  feste Liste im Runner. → Kleiner Kern-PR (§9.1), Voraussetzung für das Senden durch Agenten (M4).

## 3. Anmeldung bei den Anbietern

| Anbieter | Weg | Belege / Hinweise |
|---|---|---|
| Normaler Mailserver (Strato, IONOS, Posteo, eigener Server …) | IMAP + SMTP mit Passwort | Standard |
| **Gmail** | **a)** App-Passwort (Google-Konto mit 2-Schritt-Bestätigung) über IMAP/SMTP, **b)** OAuth (XOAUTH2) | OAuth-Bereich `https://mail.google.com/` (eingeschränkter Bereich). Eine OAuth-App im Status „Testing“ bekommt Refresh-Tokens, die **nach 7 Tagen ablaufen** (developers.google.com/identity/protocols/oauth2). Für den Eigengebrauch ist deshalb **a)** der verlässliche Weg, b) kommt optional dazu |
| **Microsoft** (Outlook.com, Microsoft 365) | OAuth 2.0 (XOAUTH2) für IMAP und SMTP, Geräte-Code-Anmeldung | Bereiche `https://outlook.office.com/IMAP.AccessAsUser.All`, `…/SMTP.Send`, `offline_access`; gilt für Microsoft 365 **und** Outlook.com (learn.microsoft.com, „Authenticate an IMAP, POP or SMTP connection using OAuth“). Braucht eine eigene App-Registrierung (Client-ID) |

- OAuth über **Geräte-Code** (Code auf microsoft.com/devicelogin eingeben). Damit braucht es keine öffentliche
  Rückleitungsadresse, und es läuft auch hinter NAT und auf dem Mac.
- Die Client-IDs trägt der Admin in den Modul-Einstellungen ein. Es gibt **keine** fest eingebauten IDs von HydraHive.
- Refresh-Tokens und Passwörter liegen verschlüsselt (gleiche AES-GCM-Funktion wie der Credential-Store, eigener
  Schlüsselbereich `mailbox`). Sie werden nie an das Frontend, Agenten, Logs oder Datamining ausgegeben.
- **Offen (Messung M1):** Ob die Microsoft-Geräte-Code-Anmeldung für ein privates Outlook.com-Konto mit
  einer selbst registrierten App ohne Prüfung durch Microsoft durchgeht, ist **nicht belegt**. Das wird mit Tills Konto geprüft,
  bevor M1b gebaut wird.

## 4. Datenmodell (eigene Tabellen `module_mailbox_*`)

- **account**: id, Besitz (`user:<id>` oder `group:<id>`), Anzeigename, Adresse, Absendername, Anmeldeart
  (`password`, `oauth_google`, `oauth_microsoft`), IMAP-Host/Port/TLS, SMTP-Host/Port/TLS, verschlüsseltes Geheimnis,
  Signatur, Status (ok, Anmeldung abgelaufen, Fehler), letzter Abgleich.
- **folder**: Konto, Name (IMAP, UTF-7 dekodiert), Rolle (Posteingang, Gesendet, Entwürfe, Papierkorb, Spam, Archiv
  aus SPECIAL-USE), UIDVALIDITY, höchste UID, Anzahl, ungelesen.
- **message**: Konto, Ordner, UID, Message-ID, In-Reply-To/References (für Unterhaltungen), Thread-ID, Datum,
  Von/An/Cc, Betreff, Kurztext, Flags (gelesen, markiert, beantwortet), Größe, Anhänge (Name, Typ, Größe),
  **Pfad der Rohmail** (`.eml`), `deleted_on_server` (siehe §5).
- **Volltext**: SQLite FTS5 über Betreff, Absender, Empfänger und Text (Klartext bzw. aus HTML gewonnen).
- **project_share**: Projekt-ID, Konto, Ordner (leer bedeutet alle), Stufe `read` | `draft` | `send`, wer und wann.
- **audit**: jede Agenten-Aktion und jeder Versand (wer, welches Projekt, welche Mail, Ergebnis). Ohne Mailinhalt.

Rohmails liegen als `.eml` im Archivordner (Aufbau §5a). Sie werden nie verändert und auch für Anhänge genutzt.
Das ist das Archiv: Jede Datei lässt sich ohne HydraHive mit jedem Mailprogramm öffnen.

## 5. Abgleich und Archiv

- Hintergrund-Job je Konto: zuerst Ordnerliste, dann je Ordner neue UIDs (UIDVALIDITY beachten) und Flags.
  **IMAP IDLE** auf dem Posteingang für sofortige neue Mails, sonst Abfrage alle 5 Minuten (einstellbar).
- Erster Abgleich: **alle Ordner, alle Mails** (Archiv). Er läuft gedrosselt (z. B. 200 Mails je Runde) und sichtbar
  mit Fortschritt. Große Postfächer brauchen Stunden, das ist in Ordnung.
- **Archiv-Regel (Till: „immer alles im Archiv behalten“)**: Das Archiv löscht **nie**. Löscht der Server eine Mail
  (auch durch ein anderes Programm oder ein geleerter Papierkorb), bleibt sie lokal und wird als `deleted_on_server`
  markiert. Sie ist im Ordner „Archiv (nur lokal)“ zu finden. Löscht der **Nutzer** in Mailbox, wird nur auf dem Server
  gelöscht, die Archivdatei bleibt. Es gibt **keine** Einstellung „auch lokal löschen“.
- Speicherplatz wird je Konto angezeigt. Wird die Platte knapp, gibt es einen Hinweis und es wird nichts gelöscht.

### 5a. Archiv als Backup

- **Aufbau, lesbar ohne HydraHive**:
  `<archiv>/<konto-adresse>/<ordner>/<jjjj>/<jjjj-mm-tt_hhmm>_<kurzbetreff>_<hash8>.eml`. Den Dateinamen bildet nur
  der Server: Betreff gekürzt, nur `[A-Za-z0-9äöüÄÖÜß_-]`, max. 60 Zeichen. Verschiebt der Nutzer eine Mail auf dem
  Server, zieht die Datei in den neuen Ordner um. Sie wird verschoben, nie gelöscht.
- **Vollständigkeit**: Je Konto eine Datei `MANIFEST.tsv` (Pfad, SHA-256, Message-ID, Server-Ordner, Status). Eine
  Prüfung (wöchentlich und auf Knopfdruck) gleicht Dateien, Hashes und Datenbank ab und meldet Fehlendes oder
  Verändertes in der Oberfläche.
- **Wiederherstellen**: Dateien lassen sich in Thunderbird (Import von `.eml`) oder in jedes IMAP-Konto hochladen.
  Optional später: „Ordner auf den Server zurückspielen“ (IMAP APPEND) in der Oberfläche.
- **Speicherort** einstellbar (Standard `<data_dir>/mailbox/archiv`), z. B. auf einer eigenen Platte. Die Datenbank
  (Index) lässt sich jederzeit aus den `.eml` neu aufbauen. Das Backup sind also die Dateien.

### 5b. Samba-Freigabe des Archivs

- Ausgangslage (geprüft 21.10.): Der Kern gibt heute **nur Projekt-Workspaces** frei, mit **einem gemeinsamen
  Samba-Nutzer** für alle Freigaben (`samba/manager.py`) und **beschreibbar**. Für ein Mailarchiv reicht das nicht:
  Jeder mit dem Samba-Passwort sähe alle Archive, und Dateien wären änderbar.
- Daher: **Kern-Erweiterung** (§9.3) für Modul-Freigaben, die
  1. **nur lesbar** sind (`read only = yes`),
  2. einen **eigenen Samba-Nutzer je HydraHive-Nutzer** haben (Passwort in HydraHive gesetzt, nur für Samba),
  3. pro HydraHive-Nutzer nur **seine** Konten zeigen (eine Freigabe `Mailarchiv-<nutzer>`). Gemeinsame Konten liegen in
     `Mailarchiv-<gruppe>` für die Mitglieder der Gruppe.
- Freigabe je Konto in der Mailbox-Oberfläche an/aus (Standard **aus**). Nur unter Linux mit installiertem Samba. Auf
  dem Mac gibt es keine Samba-Freigabe von HydraHive. Dort bleibt der Ordner im Finder bzw. die Dateifreigabe von
  macOS.

## 6. Oberfläche (Webmail)

- Drei Spalten: **Konten und Ordner** | **Mailliste** | **Lesebereich**. Auf schmalen Bildschirmen jeweils eine Spalte.
- Die Ordner jedes Kontos sind beim ersten Öffnen eingeklappt. Der Nutzer kann jedes Konto einzeln auf- und zuklappen; der Zustand bleibt in diesem Browser erhalten, bis er ihn erneut ändert. Neu hinzugefügte Konten starten ebenfalls eingeklappt.
- „Alle Posteingänge“ zusätzlich zu den einzelnen Konten. Unterhaltungen gruppiert (umschaltbar).
- Suche über alle Konten mit Filtern (von:, an:, betreff:, hat:anhang, vor:/nach:, konto:, ordner:).
- Aktionen: gelesen/ungelesen, markieren, verschieben, archivieren, löschen, Spam. Mehrfachauswahl.
- Schreiben: Antworten, Allen antworten, Weiterleiten, Anhänge, Entwürfe (lokal und im Entwürfe-Ordner des
  Servers), Signatur je Konto, Absenderkonto wählbar. Editor mit einfacher Formatierung. Gesendet wird als
  Text- und HTML-Teil.
- Tastenkürzel (j/k, r, a, f, e, #, /, c).
- **Sicheres Anzeigen** von HTML-Mails: Bereinigung auf dem Server (erlaubte Tags/Attribute), Anzeige in einem
  `iframe` mit `sandbox` ohne Skripte und ohne Formulare. **Externe Bilder** sind standardmäßig gesperrt („Bilder
  laden“ einmalig oder für diesen Absender), Links öffnen mit `noopener` und `noreferrer`.
- Benachrichtigung bei neuer Mail im Browser, optional in den Vitrine-Verlauf.
- Konten-Seite: Konto hinzufügen mit Assistent (Adresse eingeben, bekannte Anbieter füllen Host und Port aus),
  Verbindung testen, Anmeldung erneuern, Abgleich-Status.

## 7. Konten und Freigaben

- **Persönliche Konten** gehören einem Nutzer. Nur er sieht sie in der Oberfläche.
- **Gemeinsame Konten** gehören einer **Gruppe** (Freigaben & Gruppen). Alle Mitglieder sehen sie. Anlegen, Ändern
  und Entfernen dürfen nur Admins und wer das Recht `mailbox.manage_shared` hat.
- **Freigabe für ein Projekt**: Der Besitzer des Kontos (bei Gruppen: wer `mailbox.manage_shared` hat) gibt ein Konto
  (optional nur bestimmte Ordner) für ein Projekt frei, mit einer Stufe:

| Stufe | Agenten im Projekt dürfen |
|---|---|
| `read` | suchen, lesen, Anhänge in den Projekt-Workspace holen |
| `draft` | dazu Entwürfe anlegen und ändern, verschieben, markieren |
| `send` | dazu senden, **jede Mail einzeln nach Bestätigung** im Chat |

- Werkzeuge sehen **nur** Konten mit Freigabe für das aktive Projekt (`ctx.project_id`). Ohne Projekt bleibt nur ein
  persönliches Konto, und nur, wenn der Nutzer es für „Buddy“ freigibt (gleiche Stufen).
- Rechte (Capabilities): `module.mailbox` (Modul nutzen), `mailbox.manage_shared` (gemeinsame Konten verwalten).
- Option je Konto: **hinter die Vault-PIN**. Dann ist es in der Oberfläche erst nach der PIN sichtbar. Agenten-Werkzeuge
  liefern bei gesperrtem Vault `vault_locked`.

## 8. Werkzeuge für Agenten

| Werkzeug | Stufe | Zweck |
|---|---|---|
| `mailbox_accounts` | read | freigegebene Konten und Ordner des Projekts |
| `mailbox_search` | read | Suche (FTS + Filter), max. 50 Treffer, Kurzfassung je Treffer |
| `mailbox_read` | read | eine Mail oder die ganze Unterhaltung als Text, lange Texte in Abschnitten |
| `mailbox_attachment` | read | Anhang in den Projekt-Workspace speichern (Größengrenze, sichere Dateinamen) |
| `mailbox_draft` | draft | Entwurf anlegen oder ändern (neu, Antwort, Weiterleitung) |
| `mailbox_move` / `mailbox_flag` | draft | verschieben, gelesen setzen, markieren |
| `mailbox_send` | send | Entwurf senden: **immer Bestätigung** mit Absender, Empfängern, Betreff, Anhängen und Textanfang |

- **Mailinhalt ist fremder Text**: Jede Ausgabe steht zwischen `<<<MAIL-INHALT …>>>` und `<<<ENDE MAIL-INHALT>>>`, mit
  dem Hinweis, darin enthaltene Anweisungen nie zu befolgen (wie bei Discord).
- Werkzeuge geben nie Zugangsdaten, Tokens oder Header mit Authentifizierungsdaten aus.
- `sensitive_tools`: alle Lese-Werkzeuge auf Stufe `privat` (Datamining).
- Jede Aktion steht im Protokoll (§4 audit), sichtbar in der Oberfläche je Konto.
- Später (M5): `mailbox_to_case` (Mail als Schriftverkehr in die Legal-Fallakte, als **Vorschlag**), Mail → Task/Ticket.

## 9. Kern-Änderungen

1. **Bestätigung für Modul-Werkzeuge** (Voraussetzung für M4): `Tool` bekommt ein optionales
   `confirm_reason(args) -> str | None`. Der Runner fragt das zusätzlich zu `ALWAYS_CONFIRM`. Klein, mit Tests, eigener PR.
2. Keine neuen Abhängigkeiten: Standardbibliothek (`imaplib`, `smtplib`, `email`) plus das vorhandene
   `cryptography` und `httpx`.
3. **Samba-Freigaben für Module** (für §5b): nur lesbar, eigener Samba-Nutzer je HydraHive-Nutzer bzw. Gruppe, Pfad
   nur innerhalb des Datenordners des Moduls. Eigene Spec im Kern-Repo, eigener PR. Voraussetzung für M2b.

## 10. Etappen

| Etappe | Inhalt | Abnahme |
|---|---|---|
| **M1** | Konten (Passwort-IMAP/SMTP, Gmail per App-Passwort), Abgleich + Archiv + FTS, Webmail **lesen** (3 Spalten, Suche, Unterhaltungen, sichere Anzeige, Anhänge laden), persönliche Konten | Tills Mailkonto vollständig archiviert, Suche findet alte Mails, HTML-Mail ohne externe Bilder |
| **M1b** | OAuth Microsoft (Geräte-Code), danach Google-OAuth optional. **Zum Schluss** (Till: Azure-App erst dann) | Tills Microsoft-Adresse liest und sendet |
| **M2** | Schreiben, Antworten, Weiterleiten, Entwürfe, Signaturen, Verschieben, Löschen, Archiv-Regel | Mail gesendet und im Gesendet-Ordner, gelöschte Server-Mail bleibt im Archiv |
| **M2b** | Archiv als Backup (§5a: Prüfung, Manifest, Speicherort) + Kern-PR §9.3 + Samba-Freigabe nur lesbar | `Mailarchiv-till` im Datei-Manager sichtbar, nicht beschreibbar, ein fremder Nutzer sieht es nicht |
| **M3** | Gemeinsame Konten (Gruppe), Freigabe je Projekt, Werkzeuge `read` + `draft`, Protokoll | Rechts-Agent findet Mail im freigegebenen Konto, sieht ein anderes nicht |
| **M4** | Kern-PR §9.1 + `mailbox_send` mit Bestätigung | Senden nur nach „Ja“, ohne Antwort wird nicht gesendet |
| **M5** | Legal-Anbindung, Mail → Task/Ticket, Regeln/Filter, Vitrine-Hinweis | nach Bedarf |

## 11. Sicherheit (Prüfliste)

- TLS ist Pflicht (IMAPS 993 / SMTP mit STARTTLS oder TLS). Ohne TLS nur mit ausdrücklicher Freigabe je Konto
  (Warnung), z. B. für einen lokalen Testserver.
- Zertifikate werden geprüft. Eigene Zertifikate nur mit hinterlegtem Fingerabdruck.
- Hosts: keine internen Adressen ohne Admin-Freigabe (SSRF-Schutz wie bei anderen Modulen).
- Eingaben: Ordnernamen, Message-IDs und Dateinamen werden geprüft. Pfade der `.eml`-Dateien bildet nur der Server
  (Hash), nie aus Mailinhalten.
- HTML: Bereinigung auf dem Server plus `sandbox`-iframe plus CSP. Kein `innerHTML` mit Mailinhalt ohne Bereinigung.
- Rechte werden bei **jeder** Route und jedem Werkzeug geprüft (Besitz, Gruppe, Projektfreigabe, Stufe).
- Rate-Limit beim Senden (z. B. 20 je Stunde je Konto, einstellbar), damit ein Fehler im Agenten nicht massenhaft versendet.

## 12. Mac

- Nur Python-Standardbibliothek plus Kern-Abhängigkeiten. Keine Systempakete, kein Dienst außerhalb von HydraHive.
- Hintergrund-Jobs laufen im HydraHive-Prozess (`register_job`), also auch auf dem Mac.
- Test im Mac-Live-Test (Task Mac-Testrechner) bei M1.

## 13. Bewusst nicht

- POP3, Exchange-EWS/Graph-API (nur IMAP/SMTP), Kalender und Kontakte, S/MIME und PGP (später denkbar), eigene
  Spam-Erkennung (der Server filtert), automatisches Senden ohne Bestätigung.

## 14. Entschieden (Till 21.10.2026)

1. Erstabgleich: **alle Ordner, alle Jahre**.
2. **Immer alles im Archiv behalten**, auch im Webmail Gelöschtes. Das Archiv ist das Backup des Mailbestands, über
   Samba erreichbar (§5a/§5b).
3. Microsoft-App-Registrierung: **zum Schluss** (M1b wandert ans Ende, Anleitung dann).
