# Mailbox M1b – Microsoft-Anmeldung (Outlook.com, Hotmail, Microsoft 365)

Stand: **umgesetzt** 23.10.2026 (Till: „ok baue das so ein“; Client-ID **einmal global** durch den Admin,
alle Nutzer melden sich darüber an). Grundlage: SPEC.md §3 (Anmeldung), §10 (Etappe M1b), §11 (Sicherheit).

## Ziel

Ein Microsoft-Postfach lässt sich in Mailbox einbinden, **ohne Passwort**. Seit Microsoft die Passwort-Anmeldung
für IMAP/SMTP abgeschaltet hat, geht das bei Outlook.com/Hotmail/Live nur noch so. Ablauf für den Nutzer:

1. Adresse eingeben (z. B. `name@outlook.de`) → Mailbox erkennt Microsoft → Knopf **„Mit Microsoft anmelden“**.
2. Mailbox zeigt einen **Code** und den Link `microsoft.com/devicelogin`. Der Nutzer meldet sich dort an und gibt
   den Code ein (geht auch am Handy).
3. Mailbox merkt die Anmeldung von selbst, prüft IMAP und startet den Abgleich wie bei jedem anderen Konto.

Abnahme (SPEC §10): **Tills Microsoft-Adresse liest und sendet.**

## Die Client-ID (Admin, einmalig)

Microsoft lässt nur registrierte Programme an IMAP/SMTP. HydraHive bringt **keine** eingebaute ID mit (SPEC §3).
Der Admin legt bei Microsoft eine eigene App-Registrierung an und trägt deren **Client-ID** in Mailbox ein.
Ein Client-**Geheimnis** braucht es nicht (Geräte-Code ist ein „öffentlicher Client“).

- Neue Karte **„Microsoft-Anmeldung“** in den Mailbox-Einstellungen, nur für Admins sichtbar:
  - Feld **Client-ID** (GUID, wird geprüft)
  - Feld **Verzeichnis** (Standard `common` = private Konten + Firmenkonten; optional Tenant-ID einer Firma)
  - Knopf **„Prüfen“**: fragt bei Microsoft einen Geräte-Code an. Klappt das, ist die ID gültig und für
    Geräte-Code freigeschaltet. Sonst zeigt die Karte Microsofts Fehlertext (z. B. „Öffentliche Clientflows nicht
    erlaubt“).
  - Kurzanleitung zum Registrieren (unten) direkt in der Karte, dazu ein Hilfe-Artikel.
- Gespeichert in eigener Tabelle `module_mailbox_settings` (Schlüssel/Wert, Migration 002). Die Client-ID ist kein
  Geheimnis, wird aber nur Admins angezeigt.
- Ist keine Client-ID eingetragen, sieht ein normaler Nutzer bei einer Microsoft-Adresse:
  „Microsoft-Anmeldung ist noch nicht eingerichtet – bitte den Admin fragen.“

### Anleitung für die Registrierung (kommt in die Karte und in den Hilfe-Artikel)

1. `entra.microsoft.com` → **App-Registrierungen** → **Neue Registrierung**. Name z. B. „HydraHive Mailbox“.
2. Unterstützte Kontotypen: **„Konten in einem beliebigen Organisationsverzeichnis und persönliche
   Microsoft-Konten“**. Umleitungs-URI leer lassen.
3. **Authentifizierung** → **„Öffentliche Clientflows zulassen“ = Ja** → Speichern.
4. Auf der Übersicht die **„Anwendungs-ID (Client)“** kopieren → in Mailbox eintragen.

**Offen, wird beim Live-Test geklärt:** Ob Microsoft mit einem rein privaten Konto noch Registrierungen ohne
(kostenloses) Azure-Konto zulässt, und ob ein privates Outlook.com-Konto eine nicht geprüfte eigene App ohne
Sperre durchlässt (SPEC §3, „Messung M1“). Das klären wir **vor** dem Bauen mit Tills Konto, Schritt 0.

## Technik

### Anmeldung (Geräte-Code, OAuth 2.0)

- `POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode` mit Client-ID und den Bereichen
  `https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/SMTP.Send offline_access`
  (learn.microsoft.com, „Authenticate an IMAP, POP or SMTP connection using OAuth“).
- Danach im Hintergrund `POST …/oauth2/v2.0/token` (`grant_type=urn:ietf:params:oauth:grant-type:device_code`) im
  vorgegebenen Takt. Beachtet `authorization_pending`, `slow_down`, `expired_token`, `access_denied`.
- Der **device_code bleibt im Server** (im Speicher, je Nutzer, läuft ab). Das Frontend bekommt nur `user_code`,
  Link, Ablaufzeit und eine eigene Vorgangs-ID zum Abfragen des Stands.
- Nur `httpx` (schon da), keine neue Abhängigkeit (SPEC §9.2). Läuft gleich auf Linux und Mac.

### Speichern und Erneuern

- Konto mit `auth = 'oauth_microsoft'` (Spalte gibt es schon). Im verschlüsselten `secret` (gleiche AES-GCM-Funktion
  wie bisher, an die Konto-ID gebunden) liegt statt des Passworts JSON `{"refresh_token": …}`.
- Zugriffstoken (ca. 1 h gültig) nur im Speicher, mit Ablaufzeit. Vor Ablauf wird über den Refresh-Token erneuert.
  Schickt Microsoft einen **neuen** Refresh-Token mit, wird er sofort gespeichert.
- Scheitert das Erneuern endgültig (`invalid_grant`, z. B. Passwort geändert oder Zugriff entzogen) →
  Kontostatus **„Anmeldung abgelaufen“** und Knopf **„Erneut mit Microsoft anmelden“**. Das ersetzt nur den
  Token, das Archiv bleibt.

### Eine Stelle für das Einloggen

Heute rufen 8 Stellen selbst `conn.login(benutzer, passwort)` auf (Abgleich, IDLE, Aktionen, Entwürfe, Senden,
Postausgang, Kontotest). Neu: **ein** Modul `backend/auth_login.py` mit

- `imap_login(conn, acc)`: Passwort → `login`, Microsoft → `AUTHENTICATE XOAUTH2`
  (`base64("user=" + adresse + "\x01auth=Bearer " + token + "\x01\x01")`)
- `smtp_login(conn, acc)`: Passwort → `login`, Microsoft → `AUTH XOAUTH2`
- `redact(text, acc)`: entfernt Passwort **und** Tokens aus Fehlertexten

Alle 8 Stellen rufen nur noch diese Funktionen. So kann keine Stelle Microsoft vergessen.

### Konto-Assistent

- `providers.suggest()` liefert für outlook.com/hotmail/live/msn/outlook.de/hotmail.de zusätzlich
  `"auth": "oauth_microsoft"`. Der Dialog zeigt dann statt des Passwortfelds den Microsoft-Knopf.
- Microsoft 365 mit eigener Domain (`name@firma.de`): Im Dialog gibt es zusätzlich die Wahl
  **„Microsoft-Konto (Outlook/365)“** bei „Anmeldeart“. Server dann `outlook.office365.com` /
  `smtp.office365.com:587`.
- SMTP für private Konten bleibt `smtp-mail.outlook.com:587` (STARTTLS), wie schon in `providers.py`.

### API (alle mit `module.mailbox`-Freigabe; Einstellungen nur Admin)

| Methode | Pfad | Zweck |
|---|---|---|
| GET/PUT | `/settings/microsoft` | Client-ID + Verzeichnis lesen/setzen (Admin) |
| POST | `/settings/microsoft/check` | Prüfen-Knopf (Admin) |
| POST | `/oauth/microsoft/start` | Geräte-Code anfordern → `{flow_id, user_code, verification_uri, expires_in}` |
| GET | `/oauth/microsoft/{flow_id}` | Stand: `pending` / `done` / `expired` / `denied` / `error` |
| POST | `/accounts` (bestehend) | mit `auth: oauth_microsoft` und `flow_id` statt Passwort |
| POST | `/accounts/{id}/reauth` | erneute Anmeldung für ein bestehendes Konto (mit `flow_id`) |

`flow_id` gehört dem Nutzer, der ihn gestartet hat. Ein fremder Nutzer bekommt 404. Einmal benutzt = verbraucht.
Start ist begrenzt (bestehendes `ratelimit.py`).

## Sicherheit (Prüfliste)

- Refresh-/Zugriffstoken nie ans Frontend, in Logs, Fehlertexte, Datamining oder an Agenten.
- `device_code` nie ans Frontend.
- Token-Abruf nur an `login.microsoftonline.com` (feste Adresse, kein Nutzer-Input in der URL außer Tenant;
  Tenant nur `common`/`organizations`/`consumers` oder GUID bzw. Domainname, geprüft).
- XOAUTH2 nur über TLS (ist schon Pflicht).
- Nutzername im XOAUTH2-String ist die Kontoadresse (keine Steuerzeichen, geprüft wie bisher).

## Tests (TDD, zuerst rot)

- Token-Endpunkt als Attrappe (`httpx.MockTransport`): Erfolg, `authorization_pending`, `slow_down`,
  `expired_token`, `access_denied`, neuer Refresh-Token wird gespeichert, `invalid_grant` → Status abgelaufen.
- IMAP-/SMTP-Attrappen können `AUTHENTICATE XOAUTH2` bzw. `AUTH XOAUTH2` und prüfen den genauen String.
- Alle 8 Login-Stellen: Microsoft-Konto loggt per XOAUTH2 ein (Test über `auth_login`, dazu ein Test, der im Code
  kein direktes `conn.login(` außerhalb von `auth_login.py` mehr zulässt).
- Rechte: Einstellungen nur Admin; `flow_id` eines anderen Nutzers → 404; verbrauchter `flow_id` → Fehler.
- Kein Token in Antworten/Fehlertexten (Suche nach dem Testtoken in allen Antworten).
- Frontend: Dialog zeigt bei Microsoft den Knopf statt Passwort, Code-Anzeige, Fehlerzustände, Admin-Karte.

## Schritte

0. **Mit Till:** App bei Microsoft registrieren (Anleitung oben), Client-ID notieren. Einmal von Hand prüfen, dass
   sein privates Konto den Geräte-Code annimmt (kleines Testskript, nichts wird gespeichert).
1. Migration 002 + Einstellungen + Admin-Karte + Prüfen-Knopf.
2. `oauth_ms.py` (Geräte-Code, Abfragen, Erneuern) + Routen `/oauth/microsoft/…`.
3. `auth_login.py`, alle 8 Stellen umstellen (reiner Umbau, Passwort-Konten verhalten sich gleich).
4. Konto-Assistent + „Erneut anmelden“.
5. Hilfe-Artikel, Version 0.4.0, volle Modul-Tests, Live-Test mit Tills Konto (lesen, senden, IDLE, nach 1 h
   noch angemeldet), auch auf dem Mac (.186).

Nicht in M1b: Google-OAuth (bleibt App-Passwort, SPEC §3), gemeinsame Konten (M3).
